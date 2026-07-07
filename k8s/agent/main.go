package main

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/ManeT0/chaos-platform/k8s/agent/executor"
	agentpb "github.com/ManeT0/chaos-platform/k8s/agent/proto/generated"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
)

var (
	port         = flag.Int("port", 50051, "The server port")
	healthPort   = flag.Int("health-port", 8081, "The health check port")
	certFile     = flag.String("tls-cert", "/etc/certs/tls.crt", "TLS cert file")
	keyFile      = flag.String("tls-key", "/etc/certs/tls.key", "TLS key file")
	caFile       = flag.String("ca-cert", "/etc/certs/ca.crt", "CA cert file")
	insecureMode = flag.Bool("insecure", false, "Disable mTLS and run insecurely")
)

type server struct {
	agentpb.UnimplementedChaosAgentServer
	exec *executor.Executor
}

func (s *server) RunExperiment(req *agentpb.ExperimentRequest, stream agentpb.ChaosAgent_RunExperimentServer) error {
	log.Printf("Received RunExperiment request: id=%s, type=%s, duration=%d", req.ExperimentId, req.Type, req.DurationSeconds)
	return s.exec.Run(req, stream)
}

func (s *server) RollbackExperiment(ctx context.Context, req *agentpb.RollbackRequest) (*agentpb.RollbackResponse, error) {
	log.Printf("Received RollbackExperiment request: id=%s, type=%s", req.ExperimentId, req.Type)
	success, msg := s.exec.Rollback(req)
	return &agentpb.RollbackResponse{
		ExperimentId: req.ExperimentId,
		Success:      success,
		Message:      msg,
	}, nil
}

func (s *server) Healthz(ctx context.Context, req *agentpb.HealthRequest) (*agentpb.HealthResponse, error) {
	return &agentpb.HealthResponse{Status: "OK"}, nil
}

func startHealthServer(port int) {
	http.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})
	addr := fmt.Sprintf(":%d", port)
	log.Printf("Starting health server on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("Health server failed: %v", err)
	}
}

func main() {
	flag.Parse()

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	var opts []grpc.ServerOption

	if !*insecureMode {
		cert, err := tls.LoadX509KeyPair(*certFile, *keyFile)
		if err != nil {
			log.Fatalf("Failed to load server TLS cert/key: %v", err)
		}

		caCert, err := os.ReadFile(*caFile)
		if err != nil {
			log.Fatalf("Failed to read CA cert: %v", err)
		}
		certPool := x509.NewCertPool()
		if !certPool.AppendCertsFromPEM(caCert) {
			log.Fatalf("Failed to append CA cert to pool")
		}

		tlsConfig := &tls.Config{
			Certificates: []tls.Certificate{cert},
			ClientAuth:   tls.RequireAndVerifyClientCert,
			ClientCAs:    certPool,
		}
		opts = append(opts, grpc.Creds(credentials.NewTLS(tlsConfig)))
		log.Println("mTLS is enabled")
	} else {
		log.Println("WARNING: running in INSECURE mode")
	}

	grpcServer := grpc.NewServer(opts...)
	agentServer := &server{
		exec: executor.New(),
	}
	agentpb.RegisterChaosAgentServer(grpcServer, agentServer)

	go startHealthServer(*healthPort)

	go func() {
		log.Printf("Starting gRPC server on port %d", *port)
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatalf("Failed to serve: %v", err)
		}
	}()

	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c
	log.Println("Shutting down gRPC server...")
	grpcServer.GracefulStop()
}
