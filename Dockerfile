FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --create-home --uid 1000 lab

WORKDIR /workspace

COPY --chown=lab:lab pyproject.toml README.md ./
COPY --chown=lab:lab src/ src/

RUN pip install --no-cache-dir --editable '.[dev]'

USER lab

CMD ["lab-sim", "doctor"]
