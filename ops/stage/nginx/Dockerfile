# https://hub.docker.com/_/nginx
FROM nginx:1.30.0-trixie

RUN rm /etc/nginx/conf.d/default.conf

COPY vouch.conf /etc/nginx/conf.d/vouch.conf
