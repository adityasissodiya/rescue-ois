package fsm

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"sync"

	"github.com/hashicorp/raft"
)

type Event struct {
	IncidentID    string         `json:"incident_id"`
	EventSeq      uint64         `json:"event_seq"`
	EventType     string         `json:"event_type"`
	Payload       map[string]any `json:"payload"`
	DeviceID      string         `json:"device_id"`
	UserID        string         `json:"user_id"`
	ClientEventID string         `json:"client_event_id"`
	CreatedAt     string         `json:"created_at"`
}

type ApplyCmd struct {
	Op    string `json:"op"`
	Event Event  `json:"event"`
}

type ApplyResult struct {
	Status        string `json:"status"`
	ClientEventID string `json:"client_event_id"`
	EventSeq      uint64 `json:"event_seq,omitempty"`
}

type JournalFSM struct {
	mu           sync.RWMutex
	eventsByCID  map[string]struct{}
	eventsBySeq  map[string]map[uint64]Event
	nextSeqByInc map[string]uint64
}

func New() *JournalFSM {
	return &JournalFSM{
		eventsByCID:  make(map[string]struct{}),
		eventsBySeq:  make(map[string]map[uint64]Event),
		nextSeqByInc: make(map[string]uint64),
	}
}

func (f *JournalFSM) Apply(log *raft.Log) any {
	var cmd ApplyCmd
	if err := json.Unmarshal(log.Data, &cmd); err != nil {
		return err
	}

	switch cmd.Op {
	case "append":
		return f.append(cmd.Event)
	default:
		return errors.New("unknown op")
	}
}

func (f *JournalFSM) Snapshot() (raft.FSMSnapshot, error) {
	f.mu.RLock()
	defer f.mu.RUnlock()

	snap := snapshotState{
		EventsByCID:  make(map[string]struct{}, len(f.eventsByCID)),
		EventsBySeq:  make(map[string]map[uint64]Event, len(f.eventsBySeq)),
		NextSeqByInc: make(map[string]uint64, len(f.nextSeqByInc)),
	}
	for key := range f.eventsByCID {
		snap.EventsByCID[key] = struct{}{}
	}
	for incidentID, events := range f.eventsBySeq {
		snap.EventsBySeq[incidentID] = make(map[uint64]Event, len(events))
		for seq, event := range events {
			snap.EventsBySeq[incidentID][seq] = event
		}
	}
	for incidentID, seq := range f.nextSeqByInc {
		snap.NextSeqByInc[incidentID] = seq
	}

	return &journalSnapshot{state: snap}, nil
}

func (f *JournalFSM) Restore(rc io.ReadCloser) error {
	defer rc.Close()

	var snap snapshotState
	if err := json.NewDecoder(rc).Decode(&snap); err != nil {
		return fmt.Errorf("decode snapshot: %w", err)
	}

	f.mu.Lock()
	defer f.mu.Unlock()
	f.eventsByCID = snap.EventsByCID
	f.eventsBySeq = snap.EventsBySeq
	f.nextSeqByInc = snap.NextSeqByInc
	return nil
}

func (f *JournalFSM) Count(incidentID string) int {
	f.mu.RLock()
	defer f.mu.RUnlock()
	return len(f.eventsBySeq[incidentID])
}

func (f *JournalFSM) append(event Event) ApplyResult {
	f.mu.Lock()
	defer f.mu.Unlock()

	if _, duplicate := f.eventsByCID[event.ClientEventID]; duplicate {
		return ApplyResult{Status: "duplicate", ClientEventID: event.ClientEventID}
	}

	next := f.nextSeqByInc[event.IncidentID] + 1
	event.EventSeq = next
	if _, ok := f.eventsBySeq[event.IncidentID]; !ok {
		f.eventsBySeq[event.IncidentID] = make(map[uint64]Event)
	}
	f.eventsBySeq[event.IncidentID][next] = event
	f.nextSeqByInc[event.IncidentID] = next
	f.eventsByCID[event.ClientEventID] = struct{}{}

	return ApplyResult{
		Status:        "accepted",
		ClientEventID: event.ClientEventID,
		EventSeq:      next,
	}
}

type snapshotState struct {
	EventsByCID  map[string]struct{}         `json:"events_by_cid"`
	EventsBySeq  map[string]map[uint64]Event `json:"events_by_seq"`
	NextSeqByInc map[string]uint64           `json:"next_seq_by_inc"`
}

type journalSnapshot struct {
	state snapshotState
}

func (s *journalSnapshot) Persist(sink raft.SnapshotSink) error {
	if err := json.NewEncoder(sink).Encode(s.state); err != nil {
		sink.Cancel()
		return err
	}
	return sink.Close()
}

func (s *journalSnapshot) Release() {}
