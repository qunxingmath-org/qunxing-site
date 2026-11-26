# Include in the www HTTPS server after a Release mirror has passed verification.
location ^~ /download/files/ {
    alias /srv/qunxing/downloads/;
    default_type application/octet-stream;
}
