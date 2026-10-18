extends SceneTree
## Boots the crowd with samples and fully procedural, runs every reaction and
## fails on script errors or a bake that never finishes.

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var failed := false
	for samples in [true, false]:
		var crowd = load("res://addons/crowd_sound/crowd_sound.gd").new()
		crowd.use_samples = samples
		root.add_child(crowd)
		crowd.active = true
		var ready := [false]
		crowd.synth_ready.connect(func(): ready[0] = true)
		var deadline := Time.get_ticks_msec() + 60000
		while not ready[0] and Time.get_ticks_msec() < deadline:
			await process_frame
		if not ready[0]:
			push_error("crowd bake did not finish (samples: %s)" % samples)
			failed = true
		crowd.kickoff()
		crowd.hit()
		crowd.roar()
		crowd.scream(Vector3.ZERO, 0.8)
		for i in 120:
			await process_frame
		if crowd.enthusiasm <= 0.0:
			push_error("reactions did not raise enthusiasm (samples: %s)" % samples)
			failed = true
		crowd.queue_free()
		await process_frame
	print("CROWD_SMOKE_PASS" if not failed else "CROWD_SMOKE_FAIL")
	quit(1 if failed else 0)
