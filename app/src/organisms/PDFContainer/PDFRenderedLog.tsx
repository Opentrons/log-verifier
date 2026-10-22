import * as React from "react"

import type { LoadedCoalescedState } from "@/redux/pdf/hooks"

export interface PDFRenderedLogProps {
  data: LoadedCoalescedState
}

import { I18NContext, I18nContext } from "@/i18n"
import {
  AttestationConsistency,
  InternalConsistency,
  LogLine,
  SequentialConsistency,
} from "@/redux/logDirectory/types"

import styles from "./pdfrenderedlog.module.css"

function internalConsistencyShortString(internal: InternalConsistency): string {
  switch (internal.status) {
    case "consistent":
      return "internally consistent"
    case "unverified":
      return "internal consistency not verified"
    case "inconsistent": {
      switch (internal.type) {
        case "bad-crypto-id":
          return "internally inconsistent: invalid cryptographic algorithm identifier"
        case "hash-mismatch":
          return "internally inconsistent: hash mismatch"
        case "invalid-hash":
          return "internally inconsistent: hash parsing error"
        case "invalid-signature":
          return "internally inconsistent: signature parsing error"
        case "signature-mismatch":
          return "internally inconsistent: signature not verified"
        case "unknown-signature-version":
          return "internally inconsistent: unknown signature version"
      }
    }
  }
}

function identityConsistencyShortString(
  attestation: AttestationConsistency,
  internal: InternalConsistency,
): string {
  switch (attestation.status) {
    case "consistent":
      return `matched with trusted ID, ${internalConsistencyShortString(internal)}`
    case "unverified":
      return `not yet matched with trusted ID, ${internalConsistencyShortString(internal)}`
    case "inconsistent": {
      switch (attestation.type) {
        case "internally-inconsistent": {
          return `not trusted because internally inconsistent, ${internalConsistencyShortString(internal)}`
        }
        case "mismatch": {
          return `not trusted: no match with trusted ID, ${internalConsistencyShortString(internal)}`
        }
        case "no-target": {
          return `not trusted: could not find trusted ID, ${internalConsistencyShortString(internal)}`
        }
      }
    }
  }
}

function sequentialConsistencyShortString<T>(sequential: SequentialConsistency<T>): string {
  switch (sequential.status) {
    case "consistent":
      return `consistent, previous entry is ${JSON.stringify(sequential.previousId)}`
    case "unverified":
      return "not yet checked"
    case "inconsistent": {
      switch (sequential.type) {
        case "no-target":
          return "inconsistent: could not verify previous message"
        case "hash-mismatch":
          return "inconsistent: message hash does not match content"
        case "signature-mismatch":
          return "inconsistent: signature is not valid"
        case "unknown-signature-version":
          return "inconsistent: unknown signature version"
        case "bad-crypto-id":
          return "inconsistent: unknown cryptographic id"
        case "invalid-hash":
          return "inconsistent: hash could not be parsed"
        case "invalid-signature":
          return "inconsistent: signature could not be parsed"
      }
    }
  }
}

interface SummaryRowProps {
  label: string
  content: string
}
function SummaryRow({ label, content }: SummaryRowProps): React.ReactNode {
  return (
    <div className={styles.summary_row}>
      <h3 className={styles.summary_label}>{label}</h3>
      <p className={styles.summary_content}>{content}</p>
    </div>
  )
}

interface LogLineRowProps {
  line: LogLine
  dateFormatter: I18NContext["dateFormatter"]
}

function LogLineRow({ line, dateFormatter }: LogLineRowProps): React.ReactNode {
  return (
    <div className={styles.log_line_row_outer}>
      <SummaryRow label="Entry index" content={JSON.stringify(line.id)} />
      <SummaryRow
        label="Logged at"
        content={dateFormatter.format(new Date(line.payload.loggedAt))}
      />
      <SummaryRow label="Username" content={line.payload.userName} />
      <SummaryRow label="User legal name" content={line.payload.legalName} />
      <SummaryRow label="Action" content={line.payload.action} />
      <SummaryRow label="Message" content={line.payload.message} />
      <SummaryRow label="User note" content={line.payload.userNote ?? "(none)"} />
      <SummaryRow
        label="Cryptographic verification"
        content={sequentialConsistencyShortString(line.sequentialConsistency)}
      />
    </div>
  )
}

export function PDFRenderedLog({ data }: PDFRenderedLogProps): React.ReactNode {
  const { dateFormatter } = React.useContext(I18nContext)
  // oxlint-disable-next-line react/purity this is in a usememo
  const now = React.useMemo(() => new Date(), [])
  const startDate = React.useMemo(() => new Date(data.period.startDate), [data])
  const endDate = React.useMemo(() => new Date(data.period.endDate), [data])
  return (
    <div className={styles.pdf_container}>
      <div className={styles.title_container}>
        <h1 className={styles.document_title}>
          {`Robot Logs ${dateFormatter.format(new Date(data.period.startDate))} - ${
            data.period.endDate == null
              ? "Current at time of export"
              : dateFormatter.format(new Date(data.period.endDate))
          }`}
        </h1>
        <p className={styles.caption}>{`Exported ${dateFormatter.format(now)}`}</p>
      </div>
      <div className={styles.period_summary_container}>
        <SummaryRow
          label="Robot identity cryptographic verification"
          content={identityConsistencyShortString(
            data.period.attestationConsistency,
            data.period.robotId.internalConsistency,
          )}
        />
        <SummaryRow
          label="Log authenticity cryptographic verification"
          content={sequentialConsistencyShortString(data.period.sequentialConsistency)}
        />
        <SummaryRow label="Robot name" content={data.period.robotId.name} />
        <SummaryRow label="Robot serial" content={data.period.robotId.serial} />
        <SummaryRow label="Start date" content={dateFormatter.format(new Date(startDate))} />
        <SummaryRow
          label="End date"
          content={
            data.period.endDate == null
              ? "Current at time of export"
              : dateFormatter.format(new Date(endDate))
          }
        />
        <SummaryRow
          label={data.period.protocolNames.length === 1 ? "Protocol" : "Protocols"}
          content={
            data.period.protocolNames.length === 0 ? "(none)" : data.period.protocolNames.join(", ")
          }
        />
        <SummaryRow
          label={
            data.period.softwareVersions.length === 1 ? "Software version" : "Software versions"
          }
          content={
            data.period.softwareVersions.length === 0
              ? "(unknown)"
              : data.period.softwareVersions.join(", ")
          }
        />
        <SummaryRow
          label={data.period.associatedFiles.length === 1 ? "Associated file" : "Associated files"}
          content={
            data.period.associatedFiles.length === 0
              ? "(unknown)"
              : data.period.associatedFiles.join(", ")
          }
        />
        <SummaryRow label="Log entries" content={JSON.stringify(data.period.logCount)} />
      </div>
      <div className={styles.log_lines_container}>
        {data.lines.loadedLines.map((line) => (
          <LogLineRow key={line.id} line={line} dateFormatter={dateFormatter} />
        ))}
      </div>
    </div>
  )
}
