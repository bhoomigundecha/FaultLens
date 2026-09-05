import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  weight: ['300','400','500','600','700','800','900'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata = {
  title: 'FaultLens — AI-Powered Incident Investigation',
  description: 'Turning complex telemetry into clear answers.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`h-full ${inter.variable}`}>
      <body className="h-full">{children}</body>
    </html>
  );
}
