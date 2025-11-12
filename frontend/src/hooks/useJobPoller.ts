import { useEffect, useState } from "react";
import { getJob } from "../api";
import type { Job } from "../types";

export function useJobPoller(jobId?: string, intervalMs = 2500) {
	const [job, setJob] = useState<Job>();
	useEffect(() => {
		if (!jobId) return;
		let timer: number;
		let stop = false;
		const tick = async () => {
			try {
				const j = await getJob(jobId);
				if (stop) return;
				setJob(j);
				if (
					!["completed", "error", "accepted", "rejected"].includes(j.status)
				) {
					timer = window.setTimeout(tick, intervalMs);
				}
			} catch {
				/* noop */
			}
		};
		tick();
		return () => {
			stop = true;
			if (timer) clearTimeout(timer);
		};
	}, [jobId, intervalMs]);
	return job;
}
