FROM mcr.microsoft.com/dotnet/sdk:10.0-alpine AS build

WORKDIR /src

COPY global.json Teledrop.csproj ./
RUN dotnet restore Teledrop.csproj

COPY . .
RUN dotnet publish Teledrop.csproj \
    --configuration Release \
    --output /app/publish \
    --no-restore \
    /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0-alpine AS runtime

WORKDIR /app

ENV ASPNETCORE_URLS=http://+:8080 \
    SHARE_DIRECTORY=/app/share \
    MAX_UPLOAD_BYTES=1073741824

RUN mkdir -p /app/share \
    && chown app:app /app/share

COPY --from=build /app/publish ./

VOLUME ["/app/share"]
EXPOSE 8080

USER app

ENTRYPOINT ["dotnet", "Teledrop.dll"]
