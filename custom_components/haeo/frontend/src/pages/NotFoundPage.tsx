/**
 * 404 Not Found page.
 */

import Layout from "../components/Layout";

function NotFoundPage() {
  return (
    <Layout>
      <div className="not-found-page">
        <h1>Page Not Found</h1>
        <p>The requested page does not exist.</p>
        <p>
          This app should be accessed through Home Assistant&apos;s
          configuration flow.
        </p>
      </div>
    </Layout>
  );
}

export default NotFoundPage;
