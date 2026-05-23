export const metadata = {
  title: '__APP_NAME__',
  description: 'AI agent with Sardis payments',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'ui-sans-serif, system-ui, sans-serif', margin: 0 }}>
        {children}
      </body>
    </html>
  );
}
