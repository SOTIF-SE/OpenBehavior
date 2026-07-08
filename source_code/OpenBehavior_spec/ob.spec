BehOracle = F(count(changingLane(npc1)) + count(changingLane(npc2)) + count(changingLane(npc3)) + count(changingLane(npc4)) + count(changingLane(ego))) > 0
safetyOracle = G(dist(ego, npc1) > 3 and dist(ego, npc2) > 3 and dist(ego, npc3) > 3 and dist(ego, npc4) > 3)
safetyOracle = F(dist(ego, target_position) < 0)