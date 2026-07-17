FROM python@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

RUN python -m pip install --no-cache-dir \
    activegraph==1.10.0 \
    annotated-types==0.7.0 \
    click==8.4.2 \
    pydantic==2.13.4 \
    pydantic-core==2.46.4 \
    typing-extensions==4.16.0 \
    typing-inspection==0.4.2

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
