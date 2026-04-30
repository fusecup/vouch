# https://hub.docker.com/_/nginx
FROM nginx:1.30.0-trixie

RUN rm /etc/nginx/conf.d/default.conf

COPY fusecup.conf /etc/nginx/conf.d/fusecup.conf
