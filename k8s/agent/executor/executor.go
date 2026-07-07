package executor

import (
	"fmt"
	"os/exec"
	"strconv"
	"time"

	agentpb "github.com/ManeT0/chaos-platform/k8s/agent/proto/generated"
)

type Executor struct{}

func New() *Executor {
	return &Executor{}
}

func (e *Executor) Run(req *agentpb.ExperimentRequest, stream agentpb.ChaosAgent_RunExperimentServer) error {
	sendEvent := func(eventType agentpb.ExperimentEvent_EventType, msg string) {
		stream.Send(&agentpb.ExperimentEvent{
			ExperimentId: req.ExperimentId,
			EventType:    eventType,
			Message:      msg,
			Timestamp:    time.Now().Format(time.RFC3339),
		})
	}

	sendEvent(agentpb.ExperimentEvent_STARTED, "Experiment started")

	var cmd *exec.Cmd

	switch req.Type {
	case "cpu_stress":
		dur := strconv.Itoa(int(req.DurationSeconds)) + "s"
		cmd = exec.Command("stress-ng", "--cpu", "0", "--timeout", dur)
	case "memory_stress":
		dur := strconv.Itoa(int(req.DurationSeconds)) + "s"
		cmd = exec.Command("stress-ng", "--vm", "1", "--vm-bytes", "80%", "--timeout", dur)
	case "process_kill":
		targetProcess := req.Params["process_name"]
		if targetProcess == "" {
			sendEvent(agentpb.ExperimentEvent_ERROR, "Missing 'process_name' parameter")
			return fmt.Errorf("missing process_name parameter")
		}
		cmd = exec.Command("pkill", "-f", targetProcess)
	default:
		sendEvent(agentpb.ExperimentEvent_ERROR, fmt.Sprintf("Unknown experiment type: %s", req.Type))
		return fmt.Errorf("unknown experiment type: %s", req.Type)
	}

	sendEvent(agentpb.ExperimentEvent_LOG, fmt.Sprintf("Executing command: %v", cmd.Args))

	output, err := cmd.CombinedOutput()
	if err != nil {
		msg := fmt.Sprintf("Command failed: %v. Output: %s", err, string(output))
		sendEvent(agentpb.ExperimentEvent_ERROR, msg)
		return err
	}

	sendEvent(agentpb.ExperimentEvent_LOG, fmt.Sprintf("Command output: %s", string(output)))
	sendEvent(agentpb.ExperimentEvent_COMPLETED, "Experiment completed successfully")

	return nil
}

func (e *Executor) Rollback(req *agentpb.RollbackRequest) (bool, string) {
	switch req.Type {
	case "cpu_stress", "memory_stress":
		exec.Command("pkill", "-f", "stress-ng").Run()
		return true, "Killed stress-ng processes"
	case "network_latency":
		return true, "Removed tc rules (stub)"
	default:
		return true, "No rollback needed or implemented"
	}
}
