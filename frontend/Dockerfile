# Frontend Dockerfile for React/Vite with Node.js Express server
FROM node:20-slim AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application (creates dist/ with client and server)
RUN npm run build

# Production stage
FROM node:20-slim AS production

WORKDIR /app

# Copy package files for production dependencies
COPY package*.json ./

# Install only production dependencies
RUN npm ci --omit=dev

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Expose port
EXPOSE 5000

# Set environment variables
ENV NODE_ENV=production
ENV PORT=5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:5000', (r) => process.exit(r.statusCode === 200 ? 0 : 1))" || exit 1

# Run the production server
CMD ["node", "dist/index.cjs"]
