FROM golang:1.21-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /out/raftd ./cmd/raftd

FROM alpine:3.20
RUN apk add --no-cache curl
COPY --from=build /out/raftd /usr/local/bin/raftd
EXPOSE 7000 8000
ENTRYPOINT ["/usr/local/bin/raftd"]
