import process from 'node:process'
import { createServer } from 'vite'

// Exercise the default API path without reading any environment files.
delete process.env.VITE_USE_MOCKS
const server = await createServer({ envFile: false, server: { host: '127.0.0.1', port: 4174, strictPort: true } })
await server.listen()
