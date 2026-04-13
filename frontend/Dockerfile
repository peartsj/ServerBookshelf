FROM nginx:1.27-alpine

COPY . /usr/share/nginx/html
COPY docker-entrypoint.sh /docker-entrypoint.d/40-bookshelf-env.sh
RUN chmod +x /docker-entrypoint.d/40-bookshelf-env.sh
