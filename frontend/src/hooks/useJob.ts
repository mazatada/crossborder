import { useEffect, useState } from "react";
import { getJob } from "../api";
import type { Job } from "../types";

export function useJob(jobId?: string) {
	const [data, setData] = useState<Job | null>(null);
	const [loading, setLoading] = useState(!!jobId);
	useEffect(() => {
		if (!jobId) return;
		let mounted = true;
		const poll = async () => {
			const job = await getJob(jobId);
			if (!mounted) return;
			setData(job);
			if (
				job.status &&
				!["completed", "failed", "submitted"].includes(job.status)
			) {
				setTimeout(poll, 1200);
			}
		};
		setLoading(true);
		poll().finally(() => setLoading(false));
		return () => {
			mounted = false;
		};
	}, [jobId]);
	return { data, loading };
}
