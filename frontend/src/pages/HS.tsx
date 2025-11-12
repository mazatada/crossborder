import {
	Button,
	Card,
	CardContent,
	List,
	ListItem,
	ListItemText,
	Stack,
	TextField,
	Typography,
} from "@mui/material";
import { useState } from "react";
import { classifyHS } from "../api";
import SignalCard from "../components/SignalCard";
import type { HSRequest, HSResponse } from "../types";

export default function HS() {
	const [traceId, setTraceId] = useState("LAW-2025-10-10-XYZ");
	const [resp, setResp] = useState<HSResponse | null>(null);
	const [status, setStatus] = useState<"green" | "amber" | "red">("amber");
	const classify = async () => {
		const payload: HSRequest = {
			product: {
				name: "Dorayaki",
				category: "confectionery",
				process: ["baked"],
				ingredients: [{ id: "ing_wheat_flour" }],
			},
		};
		const result = await classifyHS(payload);
		setResp(result);
		const risk = result.risk_flags;
		const topCandidate = result.hs_candidates[0];
		const nextStatus =
			risk?.ad_cvd || risk?.import_alert
				? "red"
				: (topCandidate?.confidence ?? 0) < 0.6
					? "amber"
					: "green";
		setStatus(nextStatus);
	};
	return (
		<Stack spacing={2} sx={{ p: 2 }}>
			<Typography variant="h5">HS Classification</Typography>
			<SignalCard status={status} reasons={["HS", "UoM", "PN"]} />
			<Card>
				<CardContent>
					<Stack direction="row" spacing={2}>
						<TextField
							label="Trace ID"
							value={traceId}
							onChange={(e) => setTraceId(e.target.value)}
							size="small"
						/>
						<Button variant="contained" onClick={classify}>
							Classify
						</Button>
					</Stack>
					{resp && (
						<>
							<Typography sx={{ mt: 2 }} variant="subtitle1">
								Candidates
							</Typography>
							<List>
								{resp.hs_candidates.map((c) => {
									const candidateKey = `${c.code}-${c.required_uom}-${c.rationale.join("|")}`;
									return (
										<ListItem key={candidateKey} divider>
											<ListItemText
												primary={`${c.code} (${Math.round(c.confidence * 100)}%)  uom:${c.required_uom || "-"}`}
												secondary={(c.rationale || []).join(" / ")}
											/>
										</ListItem>
									);
								})}
							</List>
						</>
					)}
				</CardContent>
			</Card>
		</Stack>
	);
}
