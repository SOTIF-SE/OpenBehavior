# OpenBehavior
This is data and code about OpenBehavior
wait for time

<style>
h1 {
    text-align: center;
}

.intro {
    text-align: center;
    margin-bottom: 50px;
    color: #555;
    font-size: 1.3em;
}

.bug-container {
    margin-bottom: 140px;
}

.bug-container h1 {
    font-size: 2.2em;
}

.bug {
    margin-bottom: 60px;
}

.bug h2 {
    border-left: 6px solid #444;
    padding-left: 10px;
}

.desc {
    margin: 10px 0 20px;
    color: #444;
}

.videos {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    align-items: flex-start;
}

.video-item {
    display: flex;
    gap: 20px;
    align-items: flex-start;
    width: 100%;
    margin-bottom: 20px;
}

video {
    width: 640px;
    border: 1px solid #ccc;
    background: black;
    flex-shrink: 0;
}

.video-desc {
    flex: 1;
    min-width: 200px;
    padding: 10px;
    background: #f9f9f9;
    border-radius: 4px;
    color: #555;
    font-size: 1.2em;
    line-height: 1.5;
}

.sub-category {
    margin: 30px 0;
    padding: 20px;
    background: #f5f5f5;
    border-radius: 8px;
    border-left: 4px solid #666;
    scroll-margin-top: 20px;
}

.sub-category h3 {
    margin-top: 0;
    margin-bottom: 15px;
    color: #333;
    font-size: 1.2em;
}

nav.toc {
    margin-bottom: 30px;
    padding: 20px;
    background: #f9f9f9;
    border-radius: 8px;
}

nav.toc .nav-item {
    margin: 8px 0;
    display: flex;
    align-items: baseline;
    gap: 10px;
}

nav.toc a {
    color: #0066cc;
    text-decoration: none;
    font-weight: 500;
    min-width: 60px;
    display: inline-block;
    font-size: 1.2em;
}

nav.toc a:hover {
    text-decoration: underline;
}

nav.toc a.nav-main-category {
    font-size: 1.6em;
    font-weight: 600;
}

nav.toc .nav-desc {
    color: #666;
    font-style: italic;
    font-size: 1.1em;
    flex: 1;
}

nav.toc .nav-main-item .nav-desc {
    font-style: normal;
    font-size: 1.2em;
    font-weight: 400;
    color: #444;
}

nav.toc .nav-main-item:not(:first-of-type) {
    margin-top: 25px;
    padding-top: 20px;
    border-top: 1px solid #ddd;
}

nav.toc .nav-sub-item {
    margin-top: 12px;
    font-style: italic;
    padding-left: 20px;
}

nav.toc .nav-sub-item a::before {
    content: "• ";
    color: #666;
    margin-right: 5px;
}
</style>

<h1>OpenBehavior: A Behavior-Centric Language for Autonomous Driving Scenario Description and Generation</h1>
<p class="intro" >
This page presents multiple categories of bugs discovered in the Apollo autonomous driving system.
</p>

<div class="bug-container">
    <h1>R1-T (T-Junction)</h1>
    <section class="bug" id="r1-t">
        <h2>R1-T Series</h2>
        <div class="sub-category" id="r1-t1">
            <h3>R1-T1</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-T1/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo collides with the adversarial vehicle following its lane change.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-t2">
            <h3>R1-T2</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-T2/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Due to Apollo's failure to yield, it collides with the second left-turning vehicle.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-t3">
            <h3>R1-T3</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-T3/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Following a sudden lane change by the adversarial vehicle, Apollo makes a sharp turn and collides with a left-turning vehicle.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-t4">
            <h3>R1-T4</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-T4/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Due to Apollo's failure to yield, it collides with the third left-turning vehicle.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-t5">
            <h3>R1-T5</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-T5/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">After passing the intersection, Apollo fails to recognize the slow-moving vehicle ahead, resulting in a rear-end collision.</div>
                </div>
            </div>
        </div>
    </section>
</div>
<div class="bug-container">
    <h1>R1-X (Four-way Intersection)</h1>
    <section class="bug" id="r1-x">
        <h2>R1-X Series</h2>
        <div class="sub-category" id="r1-x1">
            <h3>R1-X1</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-X1/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Influenced by the adversarial vehicle, Apollo fails to yield at the intersection and collides with the first vehicle approaching from the right.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-x2">
            <h3>R1-X2</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-X2/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Influenced by the adversarial vehicle, Apollo fails to yield at the intersection, resulting in a side-impact collision with the first vehicle on the right.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-x3">
            <h3>R1-X3</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-X3/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo crosses the stop line and stops in the middle of the intersection, causing a collision with a vehicle approaching from the right.</div>
                </div>
            </div>
        </div>
    </section>
</div>
<div class="bug-container">
    <h1>R1-L (Highway)</h1>
    <section class="bug" id="r1-l">
        <h2>R1-L Series</h2>
        <div class="sub-category" id="r1-l1">
            <h3>R1-L1</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L1/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">The adversarial vehicle cuts in, and Apollo fails to react and brake in time, resulting in a collision.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l2">
            <h3>R1-L2</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L2/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">An NPC vehicle changes lanes, and Apollo fails to react in time, leading to a collision.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l3">
            <h3>R1-L3</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L3/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">The vehicle ahead slows down due to obstruction by an adversarial vehicle. Apollo fails to recognize the reduced speed and collides with it.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l4">
            <h3>R1-L4</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L4/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo fails to detect a vehicle approaching from the left rear and changes lanes to the left, resulting in a collision.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l5">
            <h3>R1-L5</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L5/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Despite a vehicle ahead, Apollo plans a leftward maneuver and passes extremely close to an NPC vehicle.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l6">
            <h3>R1-L6</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L6/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo fails to yield to a diagonally stopped roadside vehicle intending to change lanes, leading to a collision.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l7">
            <h3>R1-L7</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L7/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo fails to detect a traffic accident ahead and does not brake, resulting in a rear-end collision.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l8">
            <h3>R1-L8</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L8/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo changes lanes to the right and collides with a normally driving vehicle on the right.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l9">
            <h3>R1-L9</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L9/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo initiates a lane change, attempts to abort midway due to a vehicle ahead, but reacts too late and collides with the front vehicle.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l10">
            <h3>R1-L10</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L10/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo cuts in and collides with a vehicle approaching from the right rear.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l11">
            <h3>R1-L11</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L11/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Despite a vehicle on its left, Apollo proceeds with a left lane change, resulting in a side-impact collision with an NPC vehicle.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l12">
            <h3>R1-L12</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L12/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">A vehicle ahead hesitates during a lane change and comes to a stop, but Apollo continues forward and passes dangerously close to the NPC vehicle.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l13">
            <h3>R1-L13</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L13/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">Apollo slows down and brakes due to uncertainty about the adversarial vehicle ahead, and is rear-ended by a following vehicle.</div>
                </div>
            </div>
        </div>
        <div class="sub-category" id="r1-l14">
            <h3>R1-L14</h3>
            <div class="videos">
                <div class="video-item">
                    <video controls>
                        <source src="traffic_video/R1-L14/output.mp4" type="video/mp4">
                    </video>
                    <div class="video-desc">The vehicle ahead moves slowly, but Apollo fails to detect this and brake in time, resulting in a collision.</div>
                </div>
            </div>
        </div>
    </section>
</div>