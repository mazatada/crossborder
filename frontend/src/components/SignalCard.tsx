import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";
export default function SignalCard({status, reasons}:{status:"green"|"amber"|"red",reasons:string[]}) {
  const color = status==="green"?"success":status==="amber"?"warning":"error";
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6">Clearance Signal</Typography>
        <Stack direction="row" spacing={1} sx={{mt:1}}>
          <Chip label={status.toUpperCase()} color={color as any} />
          {reasons.map((r,i)=><Chip key={i} label={r} variant="outlined" />)}
        </Stack>
      </CardContent>
    </Card>
  );
}
