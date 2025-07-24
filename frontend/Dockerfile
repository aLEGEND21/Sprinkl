# --- Development Stage ---
FROM node:20-alpine AS development
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* bun.lockb* ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# --- Build Stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* bun.lockb* ./
RUN npm install
COPY . .
RUN npm run build

# --- Production Stage ---
FROM node:20-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app .
RUN npm install --omit=dev --ignore-scripts
EXPOSE 3000
CMD ["npm", "run", "start"] 