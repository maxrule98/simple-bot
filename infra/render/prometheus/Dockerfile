FROM prom/prometheus:latest

# Copy Prometheus config from repo into image
COPY config/prometheus.yml /etc/prometheus/prometheus.yml

EXPOSE 9090

CMD ["/bin/prometheus", "--config.file=/etc/prometheus/prometheus.yml", "--storage.tsdb.path=/prometheus"]
