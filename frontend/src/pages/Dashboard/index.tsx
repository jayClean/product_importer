import { useState } from 'react';
import { UploadWizard } from '../../components/UploadWizard';
import { ProductsTab } from './ProductsTab';
import { WebhooksTab } from './WebhooksTab';
import { JobsTab } from './JobsTab';
import '../../styles/components.css';

export const DashboardPage = () => {
  const [activeTab, setActiveTab] = useState<'upload' | 'products' | 'webhooks' | 'jobs'>('upload');

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Acme Product Importer</h1>
        <nav className="dashboard-nav">
          <button
            className={activeTab === 'upload' ? 'active' : ''}
            onClick={() => setActiveTab('upload')}
          >
            Upload CSV
          </button>
          <button
            className={activeTab === 'products' ? 'active' : ''}
            onClick={() => setActiveTab('products')}
          >
            Products
          </button>
          <button
            className={activeTab === 'webhooks' ? 'active' : ''}
            onClick={() => setActiveTab('webhooks')}
          >
            Webhooks
          </button>
          <button
            className={activeTab === 'jobs' ? 'active' : ''}
            onClick={() => setActiveTab('jobs')}
          >
            Import Jobs
          </button>
        </nav>
      </header>

      <main className="dashboard-content">
        {activeTab === 'upload' && <UploadWizard />}
        {activeTab === 'products' && <ProductsTab />}
        {activeTab === 'webhooks' && <WebhooksTab />}
        {activeTab === 'jobs' && <JobsTab />}
      </main>
    </div>
  );
};
