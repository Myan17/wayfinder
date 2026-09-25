package main

import (
	"fmt"
	"strings"
)

// checkRules evaluates ADR-0004's S5-1..S5-5 after quiescence. S5-3 is also observed during the run.
func (r *run) checkRules(sc scenario) []string {
	var fails []string
	add := func(format string, a ...any) { fails = append(fails, fmt.Sprintf(format, a...)) }

	// S5-1: no lost push.
	var repoD, activeD int64
	if err := r.pool.QueryRow(r.ctx, `
		SELECT r.desired_generation, g.desired_generation
		  FROM repository r JOIN generation g ON g.id = r.active_generation_id WHERE r.id = 1`).Scan(&repoD, &activeD); err != nil {
		add("S5-1: %v", err)
	} else if repoD != activeD {
		add("S5-1: repository desired %d, active generation serves %d", repoD, activeD)
	}

	// S5-2: no regression, over every activation in order (the baseline first).
	rows, err := r.pool.Query(r.ctx, `SELECT desired_generation FROM generation
		WHERE repo_id = 1 AND activated_at IS NOT NULL ORDER BY activated_at, id`)
	if err != nil {
		add("S5-2: %v", err)
	} else {
		var seq []int64
		for rows.Next() {
			var d int64
			_ = rows.Scan(&d)
			seq = append(seq, d)
		}
		rows.Close()
		for i := 1; i < len(seq); i++ {
			if seq[i] < seq[i-1] {
				add("S5-2: activations went %v", seq)
				break
			}
		}
		if len(seq) < 2 {
			add("S5-2: vacuous: only %d activation(s)", len(seq))
		}
	}

	// S5-3 at the end, too.
	r.observe()

	// S5-4: in paused scenarios, the resumed worker's generation is refused and nothing of it is live.
	if sc.injection == "pause" {
		w1 := r.procs["w1"]
		refused := false
		for _, e := range w1.events {
			if strings.HasPrefix(e, "refused") {
				refused = true
			}
			if strings.HasPrefix(e, "activated") {
				add("S5-4: the resumed worker activated: %s", e)
			}
		}
		if !refused {
			add("S5-4: the resumed worker was not refused (events %v)", w1.events)
		}
		var bad int
		_ = r.pool.QueryRow(r.ctx, `
			SELECT count(*) FROM generation g
			  JOIN occurrence o ON o.generation_id = g.id JOIN representation p ON p.id = o.representation_id
			 WHERE g.lease_token = (SELECT lease_token FROM generation WHERE id = (
			         SELECT min(id) FROM generation WHERE repo_id = 1 AND id > 1))
			   AND (g.status <> 'failed' OR p.live)`).Scan(&bad)
		if bad > 0 {
			add("S5-4: %d row(s) of the resumed worker's generation are not failed or are live", bad)
		}
	}

	// S5-5: no IndexRepo job was inserted with unique-job options.
	var unique int
	_ = r.pool.QueryRow(r.ctx, `SELECT count(*) FROM river_job WHERE kind = 'index_repo' AND unique_key IS NOT NULL`).Scan(&unique)
	if unique > 0 {
		add("S5-5: %d job(s) carried a unique key", unique)
	}
	return fails
}
