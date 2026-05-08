package main

import (
	"flag"
	"log"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/anonymous-nca-2026/rescue-ois/baseline-raft/internal/cluster"
	"github.com/anonymous-nca-2026/rescue-ois/baseline-raft/internal/fsm"
	httpsrv "github.com/anonymous-nca-2026/rescue-ois/baseline-raft/internal/http"
)

func main() {
	nodeID := flag.String("id", os.Getenv("NODE_ID"), "Raft node ID, e.g. raftd-1")
	bind := flag.String("raft-bind", os.Getenv("RAFT_BIND"), "Raft TCP bind addr, e.g. 0.0.0.0:7000")
	advertise := flag.String("raft-advertise", os.Getenv("RAFT_ADVERTISE"), "Raft advertised addr, e.g. raftd-1:7000")
	httpAddr := flag.String("http", os.Getenv("HTTP_ADDR"), "HTTP bind addr, e.g. 0.0.0.0:8000")
	peers := flag.String("peers", os.Getenv("RAFT_PEERS"), "Comma-separated id=addr peer list")
	bootstrap := flag.Bool("bootstrap", envBool("RAFT_BOOTSTRAP"), "Bootstrap the static cluster from this node")
	flag.Parse()

	if *nodeID == "" || *bind == "" || *httpAddr == "" {
		log.Fatal("NODE_ID, RAFT_BIND, HTTP_ADDR are required")
	}
	if *advertise == "" {
		*advertise = defaultAdvertiseAddr(*nodeID, *bind)
	}

	peerList := splitPeers(*peers)
	journal := fsm.New()
	r, err := cluster.New(*nodeID, *bind, *advertise, journal, peerList, *bootstrap)
	if err != nil {
		log.Fatalf("cluster.New: %v", err)
	}

	srv := httpsrv.New(r, journal)
	log.Printf(
		"raftd %s on http=%s raft_bind=%s raft_advertise=%s bootstrap=%t peers=%v",
		*nodeID,
		*httpAddr,
		*bind,
		*advertise,
		*bootstrap,
		peerList,
	)
	log.Fatal(http.ListenAndServe(*httpAddr, srv.Routes()))
}

func splitPeers(raw string) []string {
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	peers := make([]string, 0, len(parts))
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed != "" {
			peers = append(peers, trimmed)
		}
	}
	return peers
}

func defaultAdvertiseAddr(nodeID, bindAddr string) string {
	_, port, err := net.SplitHostPort(bindAddr)
	if err != nil {
		return bindAddr
	}
	return net.JoinHostPort(nodeID, port)
}

func envBool(key string) bool {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return false
	}
	parsed, err := strconv.ParseBool(value)
	return err == nil && parsed
}
