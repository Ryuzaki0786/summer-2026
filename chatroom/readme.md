
 * ============================================================
 * MULTI-CLIENT TCP CHAT SERVER
 * ============================================================
 *
 * OVERVIEW:
 * This server allows multiple clients to connect and chat in
 * real time. When one client sends a message, every other
 * connected client receives it — like a group chat.
 *
 * KEY CONCEPT — I/O MULTIPLEXING WITH select():
 * The naive approach would be one thread per client, but that's
 * expensive. Instead, we use a single loop with select().
 * select() watches multiple file descriptors at once and tells
 * us which ones have data ready to read. This lets one thread
 * handle many clients efficiently.
 *
 * Think of it like a waiter at a restaurant. Instead of standing
 * at one table waiting for an order, the waiter scans ALL tables
 * and serves whoever raises their hand. That's select().
 *
 * ARCHITECTURE:
 *   - server_fd: the "reception desk" socket that listens for
 *     new connections on port 9090
 *   - clients[]: an array of file descriptors, one per connected
 *     client. Each is a two-way communication channel.
 *   - fd_set: the set of file descriptors we ask select() to watch
 *
 * MAIN LOOP FLOW:
 *   1. Build the fd_set: add server_fd + all connected clients
 *   2. Call select() — blocks until ANY fd has activity
 *   3. If server_fd has activity → new client connecting
 *      → accept() gives us a new fd → add to clients[]
 *   4. For each client fd with activity:
 *      → read() their message
 *      → If read returns 0: client disconnected → remove them
 *      → Otherwise: broadcast message to all OTHER clients (j != i)
 *   5. Loop back to step 1
 *
 * WHY j != i IN BROADCAST:
 * When client i sends a message, we send it to every client
 * except client i. The sender already sees what they typed —
 * echoing it back would duplicate it on their screen.
 *
 * CLIENT REMOVAL TRICK:
 * When a client disconnects, we don't shift the entire array.
 * Instead: clients[i] = clients[--client_count]
 * This copies the last client into the empty slot and shrinks
 * the array. O(1) removal instead of O(n) shifting.
 *
 * NETWORKING FUNDAMENTALS USED:
 *   socket()  — create a communication endpoint
 *   bind()    — assign it a port number
 *   listen()  — mark it as a server socket
 *   accept()  — accept a new client connection (returns new fd)
 *   recv()    — read data from a client
 *   write()   — send data to a client
 *   select()  — watch multiple fds, wake on activity
 *   close()   — shut down a connection
 *
 * ============================================================
 