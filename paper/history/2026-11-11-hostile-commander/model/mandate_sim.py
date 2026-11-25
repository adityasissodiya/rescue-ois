"""Random tests of the rules of the Mandate protocol (paper, Sections 6 to 8).

This program is not a proof and it is not a model check. It makes random runs of the
rules and examines the properties of the paper after each step.

One test: officers sign grants G(k,h,b,s) and renewals R(k,e) by the rules O1 and O2.
A hostile officer signs each certificate with a probability of 0.8, with no rule. Loyal
officers stop their consent at random times. The attacker gives valid certificates to
three devices at random times. The clock of each party has a constant error of eps or less.

Properties examined after each step:
  unique-grant             one valid grant for each epoch (Lemma 2)
  separation               start >= end + F + g for a higher epoch (Lemma 3)
  single-command           F = 0: one officer with command at one real time (Theorem 3)
  two-epochs-at-one-time   two epochs with command at one real time
  tenure                   no command after t0 + H + 2 eps, where t0 is the time at which
                           n - q + 1 loyal officers do not sign for the epoch (Theorem 4)
  two-officers-one-device  commander and deputy at one device at one time (Proposition 1)
  fallback-window          orders of the deputy in one interval of length F (Proposition 1)

Usage: python3 model/mandate_sim.py [variant] [number of tests]
Variants: ok (the rules of the paper), nostartcheck (O2 without the start time),
noepochcheck (O2 without the epoch), norenewcheck (O1 without the epoch and the end time),
weakq (a quorum of a majority only).
The tests are deterministic: test i uses the seed i.
"""
import math, random, sys

def run(seed, n, f, H, g, F, eps, steps=400, variant="ok"):
    rnd = random.Random(seed)
    q = math.ceil((n + f + 1) / 2)
    if variant == "weakq":
        q = n // 2 + 1 if n // 2 + 1 <= n - f else q
    hostile = set(rnd.sample(range(n), f))
    off = {("o", u): rnd.uniform(-eps, eps) for u in range(n)}
    ndev = 3
    devoff = [-eps, eps, rnd.uniform(-eps, eps)]
    E = {u: 1 for u in range(n)}
    M = {u: 0.0 for u in range(n)}
    consent = {u: True for u in range(n)}          # consent to the holder of the epoch E[u]
    withdrawn_at = {}                               # epoch -> (time, set of loyal officers who stopped)
    stopped = {u: set() for u in range(n)}          # epochs for which loyal u never signs renewals again
    sigs = {("G", 1, 0, 1, 0.0): set(range(n))}     # certificate -> signers
    known_grants = {u: {1} for u in range(n)}
    # device state
    dev_certs = [set([("G", 1, 0, 1, 0.0)]) for _ in range(ndev)]
    anchor = [dict() for _ in range(ndev)]
    fb_first = [dict() for _ in range(ndev)]
    fb_last = [dict() for _ in range(ndev)]
    t = 0.0
    viol = []

    def valid(c):
        return len(sigs.get(c, ())) >= q
    def clock(u):
        return t + off[("o", u)]
    def dclock(i):
        return t + devoff[i]

    def holder_cmd(i, tau):
        """Officers with holder command at device i at device time tau (from its own certificates)."""
        res = set()
        for c in dev_certs[i]:
            if c[0] == "G":
                _, k, h, b, s = c
                if s <= tau and any(r[0] == "R" and r[1] == k and tau <= r[2] for r in dev_certs[i]):
                    res.add((k, h))
        return res

    def deputy_cmd(i, tau, commit=False):
        res = set()
        if F <= 0:
            return res
        for c in dev_certs[i]:
            if c[0] != "G":
                continue
            _, k, h, b, s = c
            ends = [r[2] for r in dev_certs[i] if r[0] == "R" and r[1] == k]
            if not ends or any(tau <= e for e in ends) or s > tau:
                continue
            a = anchor[i].get(k, max(ends))
            if a < tau <= a + F:
                res.add((k, b))
                if commit:
                    anchor[i].setdefault(k, a)
                    fb_first[i].setdefault(k, tau)
                    fb_last[i][k] = tau
        return res

    for step in range(steps):
        t += rnd.choice([0.0, 0.1, 0.5, 1.0, 3.0, H / 4])
        act = rnd.random()
        maxE = max(E.values())
        if act < 0.40:      # renewal request, loyal-looking or adversarial end time
            k = rnd.choice(sorted({c[1] for c in sigs if c[0] == "G"}))
            e = round(t + rnd.choice([H - 2 * eps, H, H / 2, H + eps, 2 * H, -H]), 3)
            c = ("R", k, e)
            for u in range(n):
                if u in hostile:
                    if rnd.random() < 0.8:
                        sigs.setdefault(c, set()).add(u)
                    continue
                gk = [x for x in sigs if x[0] == "G" and x[1] == k and valid(x)]
                ok = (k in known_grants[u] and gk and k == E[u] and e <= clock(u) + H
                      and consent[u] and k not in stopped[u])
                if variant == "norenewcheck":
                    ok = k in known_grants[u] and gk and consent[u]
                if ok and rnd.random() < 0.9:
                    sigs.setdefault(c, set()).add(u)
                    M[u] = max(M[u], e)
        elif act < 0.60:    # grant proposal
            j = rnd.choice([maxE, maxE + 1, maxE + 1, maxE + 2])
            h, b = rnd.sample(range(n), 2)
            s = round(t + rnd.choice([0, g, F + g, H / 2, H + F + g + 2 * eps, H]), 3)
            c = ("G", j, h, b, s)
            for u in range(n):
                if u in hostile:
                    if rnd.random() < 0.8:
                        sigs.setdefault(c, set()).add(u)
                    continue
                ok = j > E[u] and s >= M[u] + F + g
                if variant == "nostartcheck":
                    ok = j > E[u]
                if variant == "noepochcheck":
                    ok = s >= M[u] + F + g
                if ok and rnd.random() < 0.85:
                    sigs.setdefault(c, set()).add(u)
                    E[u] = max(E[u], j)
                    consent[u] = True
        elif act < 0.70:    # an officer receives a valid grant
            vg = [c for c in sigs if c[0] == "G" and valid(c)]
            c = rnd.choice(vg)
            u = rnd.randrange(n)
            known_grants[u].add(c[1])
            if u not in hostile and c[1] > E[u]:
                E[u] = c[1]
                consent[u] = True
        elif act < 0.76:    # loyal officers withdraw consent for their epoch (a mutiny)
            k = max(E.values())
            group = [u for u in range(n) if u not in hostile and E[u] == k]
            rnd.shuffle(group)
            for u in group[: rnd.randint(1, len(group))]:
                consent[u] = False
                stopped[u].add(k)
            st = {u for u in range(n) if u not in hostile and k in stopped[u]}
            # tenure clock starts when fewer than q - f loyal officers can still sign for k
            if (n - f) - len(st) < q - f and k not in withdrawn_at:
                withdrawn_at[k] = t
        else:               # the attacker delivers valid certificates to a device
            i = rnd.randrange(ndev)
            vc = [c for c in sigs if valid(c)]
            for c in rnd.sample(vc, min(len(vc), rnd.randint(1, 4))):
                dev_certs[i].add(c)
        # ---- invariants on the certificate set
        grants = {}
        for c in sigs:
            if c[0] == "G" and valid(c):
                grants.setdefault(c[1], set()).add(c)
        for k, gs in grants.items():
            if len(gs) > 1:
                viol.append(("unique-grant", k, gs))
        for c in sigs:
            if c[0] == "R" and valid(c):
                for j, gs in grants.items():
                    if j > c[1]:
                        for gcert in gs:
                            if gcert[4] < c[2] + F + g - 1e-9:
                                viol.append(("separation", c, gcert))
        # ---- command at the devices: best case for the attacker = each device has all valid certs
        allvalid = {c for c in sigs if valid(c)}
        epochs_now = set()
        for i in range(ndev):
            saved = dev_certs[i]
            dev_certs[i] = allvalid                      # potential command with every valid certificate
            hc = holder_cmd(i, dclock(i))
            dev_certs[i] = saved
            hc_own = holder_cmd(i, dclock(i))
            dc_own = deputy_cmd(i, dclock(i), commit=rnd.random() < 0.5)
            if len({x for _, x in hc_own | dc_own}) > 1:
                viol.append(("two-officers-one-device", i, hc_own, dc_own))
            for k, x in hc:
                epochs_now.add((k, x))
            for k, x in dc_own:
                epochs_now.add((k, "dep"))
            for k, x in hc:
                if k in withdrawn_at and t > withdrawn_at[k] + H + 2 * eps + 1e-9:
                    viol.append(("tenure", k, t - withdrawn_at[k]))
            for k in fb_first[i]:
                if fb_last[i][k] - fb_first[i][k] > F + 1e-9:
                    viol.append(("fallback-window", i, k))
        if len({k for k, _ in epochs_now}) > 1:
            viol.append(("two-epochs-at-one-time", t, epochs_now))
        if F <= 0 and len({x for _, x in epochs_now}) > 1:
            viol.append(("single-command", t, epochs_now))
        if viol:
            return viol[0], step
    return None, steps

if __name__ == "__main__":
    variant = sys.argv[1] if len(sys.argv) > 1 else "ok"
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    bad = 0; first = None
    for seed in range(trials):
        n, f = random.Random(seed).choice([(4, 1), (4, 1), (5, 1), (7, 2), (10, 3)])
        F = random.Random(seed + 7).choice([0.0, 0.0, 20.0])
        v, step = run(seed, n, f, H=60.0, g=1.0, F=F, eps=0.4, variant=variant)
        if v:
            bad += 1
            first = first or (seed, n, f, F, step, v)
    print(f"variant={variant} trials={trials} violations={bad}")
    if first:
        print("first:", str(first)[:600])
