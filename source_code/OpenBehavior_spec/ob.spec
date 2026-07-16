BehOracle = F(count(changingLane(npc1)) + count(changingLane(npc2)) + count(changingLane(npc3)) + count(changingLane(npc4)) + count(changingLane(ego))) > 0
safetyOracle = G(dist(ego, npc1) > 0.5 and dist(ego, npc2) > 0.5 and dist(ego, npc3) > 0.5 and dist(ego, npc4) > 0.5)
safetyOracle = F(dist(ego, target_position) < 2)