package httpsrv

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/hashicorp/raft"

	"github.com/anonymous-nca-2026/rescue-ois/baseline-raft/internal/fsm"
)

type Server struct {
	r *raft.Raft
	f *fsm.JournalFSM
}

func New(r *raft.Raft, f *fsm.JournalFSM) *Server {
	return &Server{r: r, f: f}
}

func (s *Server) Routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", s.health)
	mux.HandleFunc("/accept/event-batch", s.acceptBatch)
	mux.HandleFunc("/journal/count", s.journalCount)
	return mux
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]any{
		"status":  "ok",
		"service": "raftd",
		"role":    s.r.State().String(),
		"leader":  string(s.r.Leader()),
	})
}

func (s *Server) acceptBatch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if s.r.State() != raft.Leader {
		w.Header().Set("X-Raft-Leader", string(s.r.Leader()))
		http.Error(w, "not leader", http.StatusServiceUnavailable)
		return
	}

	var req batchReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	ack := batchAck{}
	for i := range req.Events {
		cmd := fsm.ApplyCmd{Op: "append", Event: req.Events[i]}
		buf, err := json.Marshal(cmd)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		future := s.r.Apply(buf, 5*time.Second)
		if err := future.Error(); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		switch resp := future.Response().(type) {
		case fsm.ApplyResult:
			if resp.Status == "accepted" {
				ack.Accepted++
				if resp.EventSeq > ack.LastAck {
					ack.LastAck = resp.EventSeq
				}
			} else {
				ack.Duplicates++
			}
		case error:
			http.Error(w, resp.Error(), http.StatusInternalServerError)
			return
		default:
			http.Error(w, "unexpected raft response", http.StatusInternalServerError)
			return
		}
	}

	writeJSON(w, ack)
}

func (s *Server) journalCount(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	incidentID := r.URL.Query().Get("incident_id")
	writeJSON(w, map[string]any{
		"incident_id": incidentID,
		"count":       s.f.Count(incidentID),
	})
}

func writeJSON(w http.ResponseWriter, payload any) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(payload)
}

type batchReq struct {
	Events []fsm.Event `json:"events"`
}

type batchAck struct {
	Accepted   int    `json:"accepted"`
	Duplicates int    `json:"duplicates"`
	LastAck    uint64 `json:"last_acked_seq"`
}
