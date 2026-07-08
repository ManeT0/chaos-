package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

type ExecuteRequest struct {
	Module     string `json:"module"`
	Experiment string `json:"experiment"`
	Duration   int    `json:"duration"`
	Command    string `json:"command"`
}

type ExecuteResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
	Output  string `json:"output,omitempty"`
}

var (
	agentToken = os.Getenv("AGENT_TOKEN")
	allowedIPs = os.Getenv("ALLOWED_IPS") // comma-separated
)

func authMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if allowedIPs != "" {
			ip, _, err := net.SplitHostPort(r.RemoteAddr)
			if err != nil {
				ip = r.RemoteAddr
			}
			allowed := false
			for _, allowedIP := range strings.Split(allowedIPs, ",") {
				if strings.TrimSpace(allowedIP) == ip {
					allowed = true
					break
				}
			}
			if !allowed {
				http.Error(w, "Forbidden IP", http.StatusForbidden)
				return
			}
		}

		if agentToken != "" {
			authHeader := r.Header.Get("Authorization")
			if authHeader != "Bearer "+agentToken {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}
		}

		next(w, r)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func executeHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req ExecuteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	log.Printf("Executing chaos module %s for %d seconds\n", req.Module, req.Duration)

	// Resource limits could be enforced here via systemd-run or similar wrapping
	// e.g., if req.Command != "", we run it with a timeout.
	// We'll execute the command with a context timeout.
	var outputStr string
	if req.Command != "" {
		cmdStr := strings.ReplaceAll(req.Command, "{duration}", fmt.Sprintf("%d", req.Duration))
		
		ctx, cancel := context.WithTimeout(context.Background(), time.Duration(req.Duration+10)*time.Second)
		defer cancel()

		cmd := exec.CommandContext(ctx, "sh", "-c", cmdStr)
		out, err := cmd.CombinedOutput()
		outputStr = string(out)

		if err != nil {
			if ctx.Err() == context.DeadlineExceeded {
				outputStr += "\nExecution timed out"
			}
			log.Printf("Command error: %v", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(ExecuteResponse{
				Status:  "error",
				Message: err.Error(),
				Output:  outputStr,
			})
			return
		}
	} else {
		// Wait for duration for mocked modules
		time.Sleep(time.Duration(req.Duration) * time.Second)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ExecuteResponse{
		Status:  "success",
		Message: "Chaos injected successfully",
		Output:  outputStr,
	})
}

func rollbackHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	log.Println("Rolling back chaos...")
	// Specific rollback commands can be mapped here.
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "rolled_back"})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/execute", authMiddleware(executeHandler))
	mux.HandleFunc("/rollback", authMiddleware(rollbackHandler))

	port := os.Getenv("AGENT_PORT")
	if port == "" {
		port = "8081"
	}

	srv := &http.Server{
		Addr:    ":" + port,
		Handler: mux,
	}

	go func() {
		log.Printf("Starting Chaos Agent on port %s", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server error: %s\n", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down agent...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}
	log.Println("Agent exited gracefully")
}
