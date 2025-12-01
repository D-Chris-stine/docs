FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

# 1) Install only the libs we actually need (these are the ones that usually succeed on AL2023)
RUN dnf -y update && \
    dnf -y install \
        nss \
        atk \
        at-spi2-atk \
        cairo \
        cups-libs \
        dbus-libs \
        libXcomposite \
        libXcursor \
        libXdamage \
        libXext \
        libXi \
        libXrandr \
        libXScrnSaver \
        libXtst \
        pango \
        alsa-lib \
        wget \
        unzip \
    && dnf clean all

# 2) Download Chromium + ChromeDriver (pinned)
# NOTE: these URLs are examples; you can pin to the exact versions your navigator.py expects
RUN mkdir -p /opt/chrome && \
    mkdir -p /opt/chromedriver && \
    cd /opt && \
    # --- download chromium ---
    wget -O chrome-headless.zip https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.86/linux64/chrome-linux64.zip && \
    unzip chrome-headless.zip -d /opt/chrome && \
    rm chrome-headless.zip && \
    # --- download matching chromedriver ---
    wget -O chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.86/linux64/chromedriver-linux64.zip && \
    unzip chromedriver.zip -d /opt/chromedriver && \
    rm chromedriver.zip && \
    # make driver executable
    chmod +x /opt/chromedriver/chromedriver-linux64/chromedriver

# 3) Python deps
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --target /var/task

# 4) app code
COPY app/ ./app/

# 5) env vars to help Python find chrome/chromedriver
ENV CHROME_BIN=/opt/chrome/chrome-linux64/chrome
ENV CHROMEDRIVER_PATH=/opt/chromedriver/chromedriver-linux64/chromedriver

# 6) Lambda entry point
CMD ["app.lambda_function.lambda_handler"]
