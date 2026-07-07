import os
from typing import Any, AsyncGenerator

import grpc
import grpc.aio
from kubernetes import client, config

from k8s.agent.proto.generated import chaos_agent_pb2, chaos_agent_pb2_grpc


class ChaosAgentClient:
    def __init__(
        self,
        use_mtls: bool = True,
        ca_cert_path: str = "/etc/certs/ca.crt",
        client_cert_path: str = "/etc/certs/tls.crt",
        client_key_path: str = "/etc/certs/tls.key",
    ):
        self.use_mtls = use_mtls
        self.ca_cert_path = ca_cert_path
        self.client_cert_path = client_cert_path
        self.client_key_path = client_key_path

        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config()
            except config.ConfigException:
                pass  # K8s client might not be needed if IPs are provided directly

        try:
            self.core_v1 = client.CoreV1Api()
        except Exception:
            self.core_v1 = None

    def _get_channel(self, target_ip: str, port: int = 50051) -> grpc.aio.Channel:
        target = f"{target_ip}:{port}"
        if self.use_mtls and os.path.exists(self.ca_cert_path):
            with open(self.ca_cert_path, "rb") as f:
                root_certificates = f.read()
            with open(self.client_key_path, "rb") as f:
                private_key = f.read()
            with open(self.client_cert_path, "rb") as f:
                certificate_chain = f.read()

            credentials = grpc.ssl_channel_credentials(
                root_certificates=root_certificates,
                private_key=private_key,
                certificate_chain=certificate_chain,
            )
            options = (("grpc.ssl_target_name_override", "chaos-agent"),)
            return grpc.aio.secure_channel(target, credentials, options=options)
        else:
            return grpc.aio.insecure_channel(target)

    def discover_agent_pods(self, namespace: str = "chaos-platform", label_selector: str = "app=chaos-agent") -> list[str]:
        """Returns a list of pod IPs where the agent is running"""
        if not self.core_v1:
            return []
        pods = self.core_v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        return [pod.status.pod_ip for pod in pods.items if pod.status.pod_ip]

    async def run_experiment(
        self,
        target_ip: str,
        experiment_id: str,
        experiment_type: str,
        duration_seconds: int,
        params: dict[str, str] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        if params is None:
            params = {}

        async with self._get_channel(target_ip) as channel:
            stub = chaos_agent_pb2_grpc.ChaosAgentStub(channel)
            request = chaos_agent_pb2.ExperimentRequest(
                experiment_id=experiment_id,
                type=experiment_type,
                duration_seconds=duration_seconds,
                params=params,
            )
            call = stub.RunExperiment(request)
            async for response in call:
                yield {
                    "experiment_id": response.experiment_id,
                    "event_type": chaos_agent_pb2.ExperimentEvent.EventType.Name(response.event_type),
                    "message": response.message,
                    "timestamp": response.timestamp,
                }

    async def rollback_experiment(
        self,
        target_ip: str,
        experiment_id: str,
        experiment_type: str,
        params: dict[str, str] = None,
    ) -> bool:
        if params is None:
            params = {}

        async with self._get_channel(target_ip) as channel:
            stub = chaos_agent_pb2_grpc.ChaosAgentStub(channel)
            request = chaos_agent_pb2.RollbackRequest(
                experiment_id=experiment_id,
                type=experiment_type,
                params=params,
            )
            response = await stub.RollbackExperiment(request)
            return response.success
