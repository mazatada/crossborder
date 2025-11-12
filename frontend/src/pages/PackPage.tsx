import {
	Alert,
	Button,
	Link,
	Stack,
	TextField,
	Typography,
} from "@mui/material";
import { useState } from "react";
import { createPack, mediaUrl } from "../api";
import { useJobPoller } from "../hooks/useJobPoller";

export default function PackPage() {
	const [traceId, setTraceId] = useState("LAW-TEST-001");
	const [hs, setHs] = useState("1905.90");
	const [uomReq, setUomReq] = useState("kg");
	const [uomInv, setUomInv] = useState("kg");
	const [jobId, setJobId] = useState<string>();

	const job = useJobPoller(jobId);

	const submit = async () => {
		const payload = {
			traceId,
			hs_code: hs,
			required_uom: uomReq,
			invoice_uom: uomInv,
			invoice_payload: { number: "INV-001", qty: 10, uom: uomInv },
		};
		setJobId(await createPack(payload));
	};

	return (
		<Stack spacing={2}>
			<Typography variant="h5">通関書類パック</Typography>
			<Stack direction="row" spacing={2} flexWrap="wrap">
				<TextField
					label="Trace ID"
					value={traceId}
					onChange={(e) => setTraceId(e.target.value)}
				/>
				<TextField
					label="HS"
					value={hs}
					onChange={(e) => setHs(e.target.value)}
				/>
				<TextField
					label="Required UoM"
					value={uomReq}
					onChange={(e) => setUomReq(e.target.value)}
				/>
				<TextField
					label="Invoice UoM"
					value={uomInv}
					onChange={(e) => setUomInv(e.target.value)}
				/>
				<Button variant="contained" onClick={submit}>
					生成
				</Button>
			</Stack>

			{jobId && (
				<Alert severity="info">
					Job: {jobId} / Status: {job?.status ?? "..."}
				</Alert>
			)}
			{job?.artifacts?.length ? (
				<Stack>
					{job.artifacts.map((a) => (
						<Link
							key={a.media_id}
							href={mediaUrl(a.media_id)}
							target="_blank"
							rel="noreferrer"
						>
							ダウンロード: {a.media_id} ({a.type})
						</Link>
					))}
				</Stack>
			) : null}
			{job?.error && (
				<Alert severity="error">{JSON.stringify(job.error)}</Alert>
			)}
		</Stack>
	);
}
