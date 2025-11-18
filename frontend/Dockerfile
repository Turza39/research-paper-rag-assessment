FROM node:18-alpine

WORKDIR /app

# Install dependencies first
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

ENV CHOKIDAR_USEPOLLING=true

EXPOSE 3000
CMD ["npm", "start"]
