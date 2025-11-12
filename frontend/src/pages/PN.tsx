import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import axios from "axios";
import { useState } from "react";
import { createPN } from "../api";
import { useJob } from "../hooks/useJob";

export default function PN() {
	const [traceId, setTraceId] = useState("LAW-2025-10-10-XYZ");
	const [jobId, setJobId] = useState<string>();
	const { data } = useJob(jobId);
	const [error, setError] = useState<string>();

	const submit = async () => {
		setError(undefined);
		try {
			const payload = {
				traceId,
				product: {
					description: "Sweet baked confectionery (dorayaki)",
					origin_country: "JP",
					name: "Dorayaki",
					hs_code: "1905.90",
				},
				logistics: {
					mode: "AIR" as const,
					port_of_entry: "LAX",
					arrival_date: "2025-10-15",
					quantity: 1000,
					pkg_type: "carton",
					carrier: "DHL",
				},
				importer: { name: "XYZ LLC" },
				consignee: { name: "XYZ Warehouse" },
				label_media_id: "sha256:dummy",
			};
			const jobId = await createPN(payload);
			setJobId(jobId);
		} catch (error) {
			type ApiErrorPayload = {
				errors?: string[];
				error?: { message?: string };
			};
			if (axios.isAxiosError<ApiErrorPayload>(error)) {
				setError(
					error.response?.data?.errors?.join(", ") ??
						error.response?.data?.error?.message ??
						error.message,
				);
			} else if (error instanceof Error) {
				setError(error.message);
			} else {
				setError("PN submission failed");
			}
		}
	};

	return (
		<Stack spacing={2} sx={{ p: 2 }}>
			<Typography variant="h5">FDA Prior Notice</Typography>
			{error && <Alert severity="error">{error}</Alert>}
			<Stack direction="row" spacing={2}>
				<TextField
					size="small"
					label="Trace ID"
					value={traceId}
					onChange={(e) => setTraceId(e.target.value)}
				/>
				<Button variant="contained" onClick={submit}>
					Submit PN
				</Button>
			</Stack>
			{jobId && <Alert severity="success">Submitted Job: {jobId}</Alert>}
			{data?.artifacts?.length ? (
				<Alert severity="info">Receipt: {data.artifacts[0].media_id}</Alert>
			) : null}
		</Stack>
	);
}
