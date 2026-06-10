export const metadata = {
  title: "Gerador de Assuntos",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-br">
      <body style={{margin: 0, fontFamily: "'Segoe UI', Roboto, Arial, sans-serif", background: '#f4f6f9'}}>
        {children}
      </body>
    </html>
  );
}
