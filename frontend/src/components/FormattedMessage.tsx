import React from 'react';

interface FormattedMessageProps {
  content: string;
}

/**
 * Safely parse inline markdown tokens (**bold**, *italic*) into React elements.
 * Never uses dangerouslySetInnerHTML to guarantee complete safety against XSS.
 */
function renderInlineText(text: string): React.ReactNode[] {
  // Regex matches **bold** or *italic*
  const tokenRegex = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return <em key={idx}>{part.slice(1, -1)}</em>;
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

function parseTable(tableLines: string[], key: string): React.ReactNode {
  if (tableLines.length === 0) return null;

  const rows = tableLines.map((line) => {
    const rawCells = line.split('|');
    const startIdx = rawCells[0].trim() === '' ? 1 : 0;
    const endIdx =
      rawCells[rawCells.length - 1].trim() === '' ? rawCells.length - 1 : rawCells.length;
    return rawCells.slice(startIdx, endIdx).map((c) => c.trim());
  });

  if (rows.length === 0) return null;

  const isDelimiter = (row: string[]) =>
    row.length > 0 && row.every((cell) => /^:?-+:?$/.test(cell));

  let headerRow: string[] | null = null;
  let bodyRows: string[][] = [];

  if (rows.length >= 2 && isDelimiter(rows[1])) {
    headerRow = rows[0];
    bodyRows = rows.slice(2);
  } else {
    bodyRows = rows;
  }

  return (
    <div key={key} className="message-table-wrapper">
      <table className="message-table">
        {headerRow && (
          <thead>
            <tr>
              {headerRow.map((cell, cIdx) => (
                <th key={cIdx}>{renderInlineText(cell)}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {bodyRows.map((row, rIdx) => (
            <tr key={rIdx}>
              {row.map((cell, cIdx) => (
                <td key={cIdx}>{renderInlineText(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Renders LLM message content with clean paragraph, list, table, and bold formatting.
 */
export const FormattedMessage: React.FC<FormattedMessageProps> = ({ content }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];

  let currentListItems: React.ReactNode[] = [];
  let isNumberedList = false;
  let currentTableLines: string[] = [];

  const flushTable = () => {
    if (currentTableLines.length > 0) {
      const tableNode = parseTable(currentTableLines, `tbl_${elements.length}`);
      if (tableNode) {
        elements.push(tableNode);
      }
      currentTableLines = [];
    }
  };

  const flushList = () => {
    if (currentListItems.length > 0) {
      const key = `list_${elements.length}`;
      if (isNumberedList) {
        elements.push(
          <ol key={key} className="message-list ordered">
            {currentListItems}
          </ol>
        );
      } else {
        elements.push(
          <ul key={key} className="message-list bullet">
            {currentListItems}
          </ul>
        );
      }
      currentListItems = [];
      isNumberedList = false;
    }
  };

  lines.forEach((rawLine, lineIdx) => {
    const line = rawLine.trim();

    // Check for Markdown table line
    if (line.startsWith('|') && line.endsWith('|') && line.length >= 2) {
      flushList();
      currentTableLines.push(line);
      return;
    }

    // Not a table line, flush any active table
    flushTable();

    // Horizontal rule / divider
    if (line === '---' || line === '***') {
      flushList();
      elements.push(<hr key={`hr_${lineIdx}`} className="message-divider" />);
      return;
    }

    // Unordered bullet item: "- item" or "* item"
    const bulletMatch = rawLine.match(/^(\s*)[-*]\s+(.+)$/);
    if (bulletMatch) {
      if (isNumberedList) {
        flushList();
      }
      const itemContent = bulletMatch[2];
      currentListItems.push(
        <li key={`li_${lineIdx}`}>{renderInlineText(itemContent)}</li>
      );
      return;
    }

    // Ordered numbered item: "1. item"
    const numberedMatch = rawLine.match(/^(\s*)\d+\.\s+(.+)$/);
    if (numberedMatch) {
      if (!isNumberedList && currentListItems.length > 0) {
        flushList();
      }
      isNumberedList = true;
      const itemContent = numberedMatch[2];
      currentListItems.push(
        <li key={`li_${lineIdx}`}>{renderInlineText(itemContent)}</li>
      );
      return;
    }

    // Not a list item
    flushList();

    if (!line) {
      // Empty line adds natural vertical breathing room
      return;
    }

    // Heading item: "### Heading"
    const headingMatch = line.match(/^#{1,4}\s+(.+)$/);
    if (headingMatch) {
      elements.push(
        <div key={`h_${lineIdx}`} className="message-heading">
          {renderInlineText(headingMatch[1])}
        </div>
      );
      return;
    }

    // Standard paragraph line
    elements.push(
      <p key={`p_${lineIdx}`} className="message-paragraph">
        {renderInlineText(rawLine)}
      </p>
    );
  });

  // Flush any trailing elements
  flushList();
  flushTable();

  return <div className="formatted-message">{elements}</div>;
};
