# common/email_backend.py
# Custom SMTP backend that forces IPv4 connections.
#
# On some Windows / ISP configurations, Python's smtplib resolves
# smtp.gmail.com to an IPv6 address (2001:4860:...) but the socket then
# times out because the local network or ISP drops IPv6 traffic.
#
# This backend overrides open() to resolve the host to IPv4 first,
# guaranteeing the connection uses the 74.125.x.x family.

import socket

from django.core.mail.backends.smtp import EmailBackend


class IPv4EmailBackend(EmailBackend):
    # SMTP backend that resolves smtp.gmail.com to IPv4 and connects via AF_INET.

    def open(self):
        # Same as the parent open() but forces AF_INET for the socket.
        if self.connection:
            return False

        # Resolve the hostname to IPv4 explicitly
        try:
            addr_infos = socket.getaddrinfo(
                self.host,
                self.port,
                socket.AF_INET,   # IPv4 only
                socket.SOCK_STREAM,
            )
        except OSError:
            addr_infos = []

        if addr_infos:
            _family, _type, _proto, _canonname, sockaddr = addr_infos[0]
            ipv4_host, _ = sockaddr  # e.g. '74.125.24.108'
        else:
            ipv4_host = self.host  # fallback to hostname

        connection_params = {
            'host': ipv4_host,
            'port': self.port,
        }
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        if self.use_ssl:
            connection_params.update({
                'keyfile': self.ssl_keyfile,
                'certfile': self.ssl_certfile,
            })

        try:
            self.connection = self.connection_class(**connection_params)

            # TLS upgrade (STARTTLS)
            if self.use_tls:
                self.connection.ehlo()
                if self.ssl_keyfile and self.ssl_certfile:
                    self.connection.starttls(
                        keyfile=self.ssl_keyfile,
                        certfile=self.ssl_certfile,
                    )
                else:
                    self.connection.starttls()
                self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise
