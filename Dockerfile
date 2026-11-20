# syntax=docker/dockerfile:1
# 실험 컨테이너. algorithm-env 템플릿의 Dockerfile을 이 프로젝트에 맞게 줄였다.
#
# 소스는 이미지에 굽지 않는다. compose.yml이 저장소 폴더를 /work에 바인드
# 마운트하므로, 코드는 호스트 편집기로 고치고 실행만 여기서 한다.
FROM debian:trixie-slim

# python3: 실험 코드 (표준 라이브러리만 사용)
# python3-matplotlib: 그래프 (src/plot.py)
# python-is-python3: README의 `python -m ...` 명령을 그대로 쓰기 위해
# git, less: Codespaces 터미널에서 저장소를 다루려면 컨테이너 안에도 있어야 한다
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 python3-matplotlib python-is-python3 git less ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
