# Stage 1: Build Angular App
FROM node:22 AS build
WORKDIR /app

# Install dependencies first for cache
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy source and build
COPY . .
RUN npm run build --configuration=production

# Stage 2: Serve with Nginx
FROM nginx:alpine
# Copy the build output to replace the default nginx contents.
# Note: Angular 17+ uses browser/ output folder by default, check your angular.json.
# Usually dist/web-ui-angular/browser or dist/web-ui-angular
COPY --from=build /app/dist/web-ui-angular/browser /usr/share/nginx/html

# Replace the default nginx config to support Angular router (fallback to index.html)
RUN echo "server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files \$uri \$uri/ /index.html; \
    } \
}" > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
