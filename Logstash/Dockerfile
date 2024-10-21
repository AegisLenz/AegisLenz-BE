FROM docker.elastic.co/logstash/logstash:8.15.2

# 기본 설정 파일 삭제
RUN rm -f /usr/share/logstash/pipeline/logstash.conf

# 설정 파일 복사
COPY pipeline/ /usr/share/logstash/pipeline/
COPY config/ /usr/share/logstash/config/
COPY http_ca.crt /usr/share/logstash/config/
