opcodes = {
    0: "Hello",
    1: "Identify",
    2: "Heartbeat",
    3: "Event",
    4: "Ack",
    5: "Broadcast",
    6: "Deduplication",
    7: "Client exception",

}
close = {
    4001: "Invalid Payload",  # Server
    4002: "Unknown Opcode",  # Server
    4003: "Incorrect Opcode",  # Server
    4004: "Authentication Failure",  # Server
    4005: "Not Authenticated",  # Server
    4006: "No Heartbeat",  # Server
    4007: "Too many clients",  # Server
    4999: "Fatal client exception thrown",  # Client
}
