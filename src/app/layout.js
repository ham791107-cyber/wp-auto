import './globals.css';

export const metadata = {
  title: 'AutoBlog Dashboard',
  description: '수익 자동화 통합 대시보드',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
