FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod ./
# If go.sum exists, copy it as well
# COPY go.sum ./
RUN go mod download

COPY . .

# Generate proto stubs if necessary (assuming they are already generated or we could run protoc here)
# For now, we assume they are checked into k8s/agent/proto/generated

RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o chaos-agent .

FROM gcr.io/distroless/static:nonroot
WORKDIR /
COPY --from=builder /app/chaos-agent .

# The agent needs to execute host commands (stress-ng, etc.), but distroless/static has NO shell or tools.
# Wait, if we use distroless, the agent won't have access to pkill or stress-ng unless it uses host tools.
# Since it runs as a DaemonSet with hostPID=true, it might need to execute binaries from the host filesystem.
# Alternatively, we can use an alpine base image and install stress-ng, iproute2, etc.

# Let's switch to alpine to include basic tools
FROM alpine:3.19
RUN apk add --no-cache stress-ng iproute2 procps
WORKDIR /
COPY --from=builder /app/chaos-agent .

EXPOSE 50051 8081
ENTRYPOINT ["/chaos-agent"]
