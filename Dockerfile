# htmx, PDF.js, Pretendard는 저장소에 없으므로 npm 패키지에서 가져온다. CSS를 만들지 않으므로 설치 스크립트와 플랫폼별 바이너리는 건너뛴다.
FROM --platform=$BUILDPLATFORM node:24-alpine AS assets

WORKDIR /src

COPY src/Teledrop.Infrastructure/package.json src/Teledrop.Infrastructure/package-lock.json ./
COPY src/Teledrop.Infrastructure/scripts/ scripts/
RUN npm ci --ignore-scripts --omit=optional \
    && node scripts/vendor.mjs

# 빌드는 러너 아키텍처에서 하고 대상 아키텍처용으로 publish한다.
FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0-alpine AS build
ARG TARGETARCH

WORKDIR /src

COPY global.json ./
COPY src/Teledrop.Core/Teledrop.Core.csproj src/Teledrop.Core/
COPY src/Teledrop.Infrastructure/Teledrop.Infrastructure.csproj src/Teledrop.Infrastructure/
COPY src/Teledrop/Teledrop.csproj src/Teledrop/
RUN dotnet restore src/Teledrop/Teledrop.csproj --arch $TARGETARCH

COPY src/Teledrop.Core/ src/Teledrop.Core/
COPY src/Teledrop.Infrastructure/ src/Teledrop.Infrastructure/
COPY src/Teledrop/ src/Teledrop/
COPY --from=assets /src/wwwroot/ src/Teledrop.Infrastructure/wwwroot/
RUN dotnet publish src/Teledrop/Teledrop.csproj \
    --configuration Release \
    --arch $TARGETARCH \
    --output /app/publish \
    --no-restore \
    /p:UseAppHost=false \
    && mkdir -p /app/volume/share

# 한국어·영어 문화권과 TZ를 쓰므로 ICU와 tzdata가 들어 있는 extra 변형을 쓴다.
FROM mcr.microsoft.com/dotnet/aspnet:10.0-alpine-extra AS runtime

WORKDIR /app

ENV ASPNETCORE_URLS=http://+:8080 \
    SHARE_DIRECTORY=/app/share \
    MAX_UPLOAD_BYTES=1073741824

# 런타임 단계에서 명령을 실행하지 않으므로 arm64 이미지도 QEMU 없이 만든다.
COPY --from=build --chown=app:app /app/volume/ ./
COPY --from=build /app/publish ./

VOLUME ["/app/share"]
EXPOSE 8080

USER app

ENTRYPOINT ["dotnet", "Teledrop.dll"]
