// Extract C4 entity coordinates; never substitute the planter/dropper position.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/golang/geo/r3"
	"math"
	"os"
	"sort"
	"strconv"

	dem "github.com/markus-wa/demoinfocs-golang/v5/pkg/demoinfocs"
	"github.com/markus-wa/demoinfocs-golang/v5/pkg/demoinfocs/events"
	st "github.com/markus-wa/demoinfocs-golang/v5/pkg/demoinfocs/sendtables"
)

type Sample struct {
	Tick           int     `json:"tick"`
	Class          string  `json:"class"`
	EntityID       int     `json:"entity_id"`
	Serial         int     `json:"serial"`
	CreatedTick    int     `json:"created_tick"`
	PositionValid  bool    `json:"position_valid"`
	X              float64 `json:"X"`
	Y              float64 `json:"Y"`
	Z              float64 `json:"Z"`
	CarrierSteamID string  `json:"carrier_steamid,omitempty"`
	CarrierName    string  `json:"carrier_name,omitempty"`
	OwnerHandle    *uint64 `json:"owner_handle,omitempty"`
	Site           *int    `json:"site,omitempty"`
	Ticking        *bool   `json:"ticking,omitempty"`
	Defused        *bool   `json:"defused,omitempty"`
}

type Stream struct {
	Schema   int      `json:"schema"`
	Parser   string   `json:"parser"`
	TickRate float64  `json:"tick_rate"`
	Samples  []Sample `json:"samples"`
}

func boolProperty(e st.Entity, name string) *bool {
	if v, ok := e.PropertyValue(name); ok && v.Any != nil {
		b := v.BoolVal()
		return &b
	}
	return nil
}

// Source 2 can replace an entity slot without destroying the previous Go object.
// Keep only the exact object currently registered by the parser, including serial/class.
func pruneReplacedEntities(tracked map[int]st.Entity, created map[int]int, live map[int]st.Entity) {
	for id, entity := range tracked {
		if live[id] != entity {
			delete(tracked, id)
			delete(created, id)
		}
	}
}

func run(path string) error {
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()
	p := dem.NewParser(file)
	defer p.Close()
	entities := map[int]st.Entity{}
	created := map[int]int{}
	framesByTick := map[int][]Sample{}
	stream := Stream{Schema: 1, Parser: "demoinfocs-golang/v5 v5.2.0", Samples: []Sample{}}
	p.RegisterEventHandler(func(events.DataTablesParsed) {
		for _, name := range []string{"CC4", "CPlantedC4"} {
			class := p.ServerClasses().FindByName(name)
			if class == nil {
				continue
			}
			class.OnEntityCreated(func(e st.Entity) {
				entities[e.ID()] = e
				created[e.ID()] = p.GameState().IngameTick()
				e.OnDestroy(func() {
					if current, ok := entities[e.ID()]; ok && current.SerialNum() == e.SerialNum() {
						delete(entities, e.ID())
						delete(created, e.ID())
					}
				})
			})
		}
	})
	p.RegisterEventHandler(func(events.FrameDone) {
		tick := p.GameState().IngameTick()
		if tick < 0 {
			return
		}
		frameSamples := []Sample{}
		pruneReplacedEntities(entities, created, p.GameState().Entities())
		for _, e := range entities {
			valid := true
			for _, name := range []string{"CBodyComponent.m_cellX", "CBodyComponent.m_cellY", "CBodyComponent.m_cellZ", "CBodyComponent.m_vecX", "CBodyComponent.m_vecY", "CBodyComponent.m_vecZ"} {
				v, ok := e.PropertyValue(name)
				if !ok || v.Any == nil {
					valid = false
					break
				}
			}
			pos := r3.Vector{}
			if valid {
				pos = e.Position()
			}
			if math.IsNaN(pos.X) || math.IsNaN(pos.Y) || math.IsNaN(pos.Z) || math.IsInf(pos.X, 0) || math.IsInf(pos.Y, 0) || math.IsInf(pos.Z, 0) {
				continue
			}
			s := Sample{Tick: tick, Class: e.ServerClass().Name(), EntityID: e.ID(), Serial: e.SerialNum(), CreatedTick: created[e.ID()], PositionValid: valid, X: pos.X, Y: pos.Y, Z: pos.Z}
			if v, ok := e.PropertyValue("m_hOwnerEntity"); ok && v.Any != nil {
				handle := v.Handle()
				s.OwnerHandle = &handle
				if s.Class == "CC4" {
					if owner := p.GameState().Participants().FindByPawnHandle(handle); owner != nil {
						s.CarrierSteamID = strconv.FormatUint(owner.SteamID64, 10)
						s.CarrierName = owner.Name
					}
				}
			}
			if s.Class == "CPlantedC4" {
				s.Ticking = boolProperty(e, "m_bBombTicking")
				s.Defused = boolProperty(e, "m_bBombDefused")
				if v, ok := e.PropertyValue("m_nBombSite"); ok && v.Any != nil {
					site := v.Int()
					s.Site = &site
				}
			}
			frameSamples = append(frameSamples, s)
		}
		if len(frameSamples) == 0 {
			frameSamples = append(frameSamples, Sample{Tick: tick, Class: "unavailable", EntityID: -1})
		}
		// A tick can span multiple demo packets. The final complete snapshot wins.
		framesByTick[tick] = frameSamples
	})
	if err = p.ParseToEnd(); err != nil {
		return fmt.Errorf("C4 entity extraction: %w", err)
	}
	frameTicks := make([]int, 0, len(framesByTick))
	for tick := range framesByTick {
		frameTicks = append(frameTicks, tick)
	}
	sort.Ints(frameTicks)
	for _, tick := range frameTicks {
		stream.Samples = append(stream.Samples, framesByTick[tick]...)
	}
	stream.TickRate = p.TickRate()
	sort.SliceStable(stream.Samples, func(i, j int) bool {
		a, b := stream.Samples[i], stream.Samples[j]
		if a.Tick != b.Tick {
			return a.Tick < b.Tick
		}
		if a.EntityID != b.EntityID {
			return a.EntityID < b.EntityID
		}
		return a.Serial < b.Serial
	})
	if len(stream.Samples) == 0 {
		return fmt.Errorf("no CC4/CPlantedC4 entity samples in demo")
	}
	return json.NewEncoder(os.Stdout).Encode(stream)
}

func main() {
	path := flag.String("demo", "", "path to CS2 .dem")
	flag.Parse()
	if *path == "" {
		fmt.Fprintln(os.Stderr, "required: -demo path.dem")
		os.Exit(2)
	}
	if err := run(*path); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
