import React from 'react';
import styles from './Table.module.css';

export interface TableColumn<T> {
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  mono?: boolean;
  align?: 'left' | 'center' | 'right';
  width?: string;
}

export interface TableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  keyExtractor: (row: T, index: number) => string | number;
  className?: string;
}

export function Table<T>({ columns, data, keyExtractor, className = '' }: TableProps<T>) {
  return (
    <div className={`${styles.tableContainer} ${className}`}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((col, idx) => (
              <th
                key={idx}
                style={{ width: col.width }}
                className={
                  col.align === 'right'
                    ? styles.alignRight
                    : col.align === 'center'
                    ? styles.alignCenter
                    : ''
                }
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr key={keyExtractor(row, rowIdx)}>
              {columns.map((col, colIdx) => {
                const content =
                  typeof col.accessor === 'function'
                    ? col.accessor(row)
                    : (row[col.accessor] as unknown as React.ReactNode);

                return (
                  <td
                    key={colIdx}
                    className={`
                      ${col.mono ? styles.mono : ''}
                      ${col.align === 'right' ? styles.alignRight : ''}
                      ${col.align === 'center' ? styles.alignCenter : ''}
                    `}
                  >
                    {content}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
