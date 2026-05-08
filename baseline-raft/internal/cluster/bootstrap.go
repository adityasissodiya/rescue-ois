package cluster

import (
	"fmt"
	"net"
	"os"
	"strings"
	"time"

	"github.com/hashicorp/raft"
)

func New(nodeID, bindAddr, advertiseAddr string, fsm raft.FSM, peers []string, bootstrap bool) (*raft.Raft, error) {
	cfg := raft.DefaultConfig()
	cfg.LocalID = raft.ServerID(nodeID)
	cfg.SnapshotInterval = 60 * time.Second
	cfg.SnapshotThreshold = 8192

	advertise, err := net.ResolveTCPAddr("tcp", advertiseAddr)
	if err != nil {
		return nil, fmt.Errorf("resolve advertise addr: %w", err)
	}
	transport, err := raft.NewTCPTransport(bindAddr, advertise, 3, 10*time.Second, os.Stderr)
	if err != nil {
		return nil, fmt.Errorf("new TCP transport: %w", err)
	}

	store := raft.NewInmemStore()
	snapStore := raft.NewInmemSnapshotStore()

	r, err := raft.NewRaft(cfg, fsm, store, store, snapStore, transport)
	if err != nil {
		return nil, fmt.Errorf("new raft: %w", err)
	}

	if bootstrap {
		servers := make([]raft.Server, 0, len(peers)+1)
		servers = append(servers, raft.Server{
			Suffrage: raft.Voter,
			ID:       cfg.LocalID,
			Address:  raft.ServerAddress(advertiseAddr),
		})
		for _, peer := range peers {
			id, addr, ok := splitPeer(peer)
			if !ok {
				return nil, fmt.Errorf("invalid peer %q, expected id=addr", peer)
			}
			servers = append(servers, raft.Server{
				Suffrage: raft.Voter,
				ID:       raft.ServerID(id),
				Address:  raft.ServerAddress(addr),
			})
		}
		future := r.BootstrapCluster(raft.Configuration{Servers: servers})
		if err := future.Error(); err != nil {
			return nil, fmt.Errorf("bootstrap cluster: %w", err)
		}
	}

	return r, nil
}

func splitPeer(peer string) (id string, addr string, ok bool) {
	id, addr, ok = strings.Cut(peer, "=")
	if !ok || id == "" || addr == "" {
		return "", "", false
	}
	return id, addr, true
}
