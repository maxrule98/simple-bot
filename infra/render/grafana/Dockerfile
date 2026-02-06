FROM grafana/grafana:latest

# Copy provisioning and dashboards so Grafana starts up pre-provisioned
COPY config/grafana/provisioning /etc/grafana/provisioning
COPY config/grafana/dashboards /var/lib/grafana/dashboards

ENV GF_PATHS_PROVISIONING=/etc/grafana/provisioning
EXPOSE 3000

CMD ["/run.sh"]
