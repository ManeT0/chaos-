const statusNode = document.querySelector("#status");
const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

socket.addEventListener("open", () => {
  statusNode.textContent = "Connected to chaos event stream";
});

socket.addEventListener("message", (event) => {
  statusNode.textContent = event.data;
});

socket.addEventListener("close", () => {
  statusNode.textContent = "Disconnected from chaos event stream";
});
