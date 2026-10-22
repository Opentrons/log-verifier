import type { State, LogPeriodFile } from "./types"
/**
 * Find a period entry in the shell state.
 *
 * @param {State} state: The shell state.
 * @param {string} logToFind: The path to the period zip, in full.
 * @returns {LogPeriodFile}: The log period object, if it exists.
 * @throws {Error} If the file has no entry.
 */
export function findPeriod(state: State, logToFind: string): LogPeriodFile {
  const foundRobot = Object.entries(state).find(
    ([, entry]) => entry.periods.find((file) => file.periodZip === logToFind) != null,
  )
  if (foundRobot == null) {
    throw new Error(`Could not find robot containing log ${logToFind}`)
  }
  const [robotName, robotEntry] = foundRobot
  const foundPeriod = robotEntry.periods.find((file) => file.periodZip === logToFind)
  if (foundPeriod == null) {
    throw new Error(`Could not find log ${logToFind} in robot ${robotName}`)
  }
  return foundPeriod
}
