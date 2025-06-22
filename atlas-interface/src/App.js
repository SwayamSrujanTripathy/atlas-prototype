import React, { useState, useEffect, useCallback } from 'react';
import AWS from 'aws-sdk';
import { CheckCircle, XCircle, AlertCircle, Info, MessageSquare, DollarSign, Repeat, Package } from 'lucide-react'; // Removed PlayCircle as button is removed

// Helper component to display analysis results consistently
const AnalysisResult = ({ title, status, details, isAnomaly = false, isSuspicious = false }) => {
    let icon = <Info className="inline-block mr-2" size={18} />;
    let statusText = 'N/A';
    let textColor = 'text-gray-600';

    if (isAnomaly || isSuspicious) {
        icon = <AlertCircle className="inline-block mr-2 text-yellow-500" size={18} />;
        statusText = 'Suspicious';
        textColor = 'text-yellow-700';
    } else if (typeof status === 'boolean') {
        if (status) { // e.g., is_anomaly: false (meaning NOT an anomaly/fake)
            icon = <CheckCircle className="inline-block mr-2 text-green-500" size={18} />;
            statusText = 'Normal';
            textColor = 'text-green-700';
        } else { // e.g., is_anomaly: true (meaning IS an anomaly/fake)
            icon = <XCircle className="inline-block mr-2 text-red-500" size={18} />;
            statusText = 'Anomaly Detected';
            textColor = 'text-red-700';
            if (title === 'Review Authenticity' && status === false) { // Specific for LLM assuming not fake, if it failed
                statusText = 'Assumed Not Fake (LLM Error)';
                textColor = 'text-gray-500'; // Gray for assumed
            }
        }
    } else if (typeof status === 'string') {
        statusText = status;
        if (status.toLowerCase().includes('match')) {
            icon = <CheckCircle className="inline-block mr-2 text-green-500" size={18} />;
            textColor = 'text-green-700';
        } else if (status.toLowerCase().includes('none')) {
            icon = <XCircle className="inline-block mr-2 text-red-500" size={18} />;
            textColor = 'text-red-700';
        }
    }

    return (
        <div className={`p-2 rounded-md ${textColor}`}>
            <p className="font-semibold text-lg flex items-center">
                {icon} {title}: <span className="ml-2 font-normal text-gray-800">{statusText}</span>
            </p>
            {details && <p className="text-sm italic ml-7">{details}</p>}
        </div>
    );
};

function FeedbackForm() {
    const [feedback, setFeedback] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        console.log('User Feedback Submitted:', feedback);
        // Changed from alert() to console.log() for better compatibility in iframe environments
        console.log('Thank you for your feedback! (See console for confirmation)');
        setFeedback('');
    };

    return (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-md w-full max-w-lg mx-auto mt-8">
            <h3 className="text-2xl font-bold text-gray-800 mb-4 text-center">Provide Feedback</h3>
            <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Enter your feedback or report an issue here..."
                className="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:ring-blue-500 focus:border-blue-500 text-gray-700"
                rows="4"
            />
            <button
                type="submit"
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition duration-300 shadow-md"
            >
                Submit Feedback
            </button>
        </form>
    );
}

function App() {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    // Removed pipelineStatus and isPipelineRunning states as the button is removed
    // const [pipelineStatus, setPipelineStatus] = useState('');
    // const [isPipelineRunning, setIsPipelineRunning] = useState(false);

    // AWS SDK configuration outside useEffect for consistent S3 client
    AWS.config.update({ region: 'ap-south-1', credentials: new AWS.Credentials('test', 'test') });
    const s3 = new AWS.S3({
        endpoint: 'http://localhost:4566', // Correct LocalStack S3 endpoint
        s3ForcePathStyle: true // Required for LocalStack
    });

    const fetchProductDataFromS3 = useCallback(async () => {
        setLoading(true);
        setError(null);
        const data = [];
        const numProducts = 8; // Loop only for the 8 products you are generating
        for (let i = 1; i <= numProducts; i++) {
            try {
                const obj = await s3.getObject({ Bucket: 'atlas-results-local', Key: `analyzed/P${i}.json` }).promise();
                data.push(JSON.parse(obj.Body.toString()));
            } catch (e) {
                // Console error for missing files is expected if pipeline hasn't run yet
                // console.error(`Error fetching P${i}.json:`, e); // Commented out to reduce console noise during initial empty state
            }
        }
        setProducts(data);
        setLoading(false);
    }, [s3]); // Depend on s3 client

    // Removed handleStartPipeline function as the button is removed
    // const handleStartPipeline = async () => {
    //     setPipelineStatus('Starting pipeline...');
    //     setIsPipelineRunning(true);
    //     try {
    //         const response = await fetch('http://localhost:5000/start-pipeline'); // Call your new API endpoint
    //         if (!response.ok) {
    //             throw new Error(`HTTP error! status: ${response.status}`);
    //         }
    //         const data = await response.json();
    //         setPipelineStatus(`Pipeline: ${data.message}`);
    //         console.log("Pipeline API response:", data);
    //         setTimeout(async () => {
    //             await fetchProductDataFromS3();
    //         }, 5000);
    //     } catch (e) {
    //         setPipelineStatus(`Pipeline Error: ${e.message}`);
    //         setError(`Failed to trigger pipeline: ${e.message}`);
    //         console.error("Error calling pipeline API:", e);
    //     } finally {
    //         setIsPipelineRunning(false);
    //     }
    // };

    // Initial fetch when component mounts
    useEffect(() => {
        fetchProductDataFromS3();
        // Set up polling for continuous updates
        const intervalId = setInterval(fetchProductDataFromS3, 10000);
        return () => clearInterval(intervalId); // Cleanup on unmount
    }, [fetchProductDataFromS3]); // Depend on the memoized fetch function

    return (
        <div className="min-h-screen bg-gray-100 p-8 font-inter antialiased">
            <header className="text-center mb-12">
                <h1 className="text-5xl font-extrabold text-gray-900 leading-tight mb-4">
                    <Package className="inline-block mr-4 text-indigo-600" size={50} />
                    ATLAS 2.0 - Product Authenticity
                </h1>
                <p className="text-xl text-gray-700 max-w-2xl mx-auto">
                    Real-time insights into product authenticity, supply chain, and seller behavior.
                </p>
                {/* Removed the button and pipeline status display */}
                {/* <div className="mt-6 flex flex-col items-center">
                    <button
                        onClick={handleStartPipeline}
                        disabled={isPipelineRunning}
                        className={`px-8 py-4 rounded-xl font-bold text-lg transition duration-300 shadow-lg flex items-center justify-center
                            ${isPipelineRunning ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700 text-white'}
                        `}
                    >
                        <PlayCircle className="mr-3" size={24} />
                        {isPipelineRunning ? 'Pipeline Running...' : 'Start Full Pipeline'}
                    </button>
                    {pipelineStatus && (
                        <p className={`mt-3 text-sm ${error ? 'text-red-600' : 'text-gray-700'}`}>
                            {pipelineStatus}
                        </p>
                    )}
                </div> */}
            </header>

            {loading && <p className="text-center text-indigo-600 text-xl font-semibold">Loading product data...</p>}
            {error && <p className="text-center text-red-600 text-xl font-semibold">Error: {error}</p>}

            {!loading && products.length === 0 && !error && (
                <p className="text-center text-gray-600 text-xl">No product data available. Please ensure your backend scripts (mock_data.py, kafka_producer.py, ai_agents.py) are running manually to generate data.</p>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
                {products.map(product => (
                    <div key={product.product_id} className="bg-white rounded-xl shadow-lg p-6 flex flex-col justify-between">
                        <div>
                            <h2 className="text-3xl font-bold text-gray-800 mb-4 flex items-center">
                                Product {product.product_id}
                                {product.is_fake ? (
                                    <XCircle className="ml-3 text-red-500" size={30} />
                                ) : (
                                    <CheckCircle className="ml-3 text-green-500" size={30} />
                                )}
                            </h2>
                            <p className="text-lg text-gray-700 mb-2">
                                <span className="font-semibold">Overall Fake Status: </span>
                                <span className={product.is_fake ? 'text-red-600' : 'text-green-600'}>
                                    {product.is_fake ? 'DETECTED AS FAKE' : 'AUTHENTIC'}
                                </span>
                            </p>
                            {product.fake_reasons && product.fake_reasons.length > 0 && (
                                <p className="text-sm text-red-500 italic mb-2">
                                    Reasons: {product.fake_reasons.join(', ')}
                                </p>
                            )}
                            <p className="text-lg text-gray-700 mb-4">
                                <span className="font-semibold">Supply Verified: </span>
                                <span className={product.supply_verified ? 'text-green-600' : 'text-red-600'}>
                                    {product.supply_verified ? 'Yes' : 'No'}
                                </span>
                            </p>

                            <hr className="my-4 border-gray-200" />

                            <h3 className="text-xl font-bold text-gray-800 mb-3">Analysis Results:</h3>
                            <div className="space-y-2">
                                <AnalysisResult
                                    title="Product Vision (Logo Match)"
                                    status={product.analysis_results?.product_vision_analysis?.logo_match || 'None'}
                                    details={
                                        product.analysis_results?.product_vision_analysis?.visual_cues?.length > 0
                                            ? `Cues: ${product.analysis_results.product_vision_analysis.visual_cues.join(', ')}`
                                            : 'No visual cues.'
                                    }
                                />
                                <AnalysisResult
                                    title="Pricing Anomaly"
                                    status={!product.analysis_results?.pricing_anomaly?.is_anomaly}
                                    isAnomaly={product.analysis_results?.pricing_anomaly?.is_anomaly}
                                    details={product.analysis_results?.pricing_anomaly?.is_anomaly ? 'Price detected as outlier.' : 'Price is within expected range.'}
                                />
                                <AnalysisResult
                                    title="Return Anomaly"
                                    status={!product.analysis_results?.return_anomaly?.is_anomaly}
                                    isAnomaly={product.analysis_results?.return_anomaly?.is_anomaly}
                                    details={product.analysis_results?.return_anomaly?.is_anomaly ? 'Return rate detected as unusually high.' : 'Return rate is normal.'}
                                />
                                <AnalysisResult
                                    title="Review Authenticity"
                                    status={!product.analysis_results?.review_authenticity?.is_fake}
                                    isAnomaly={product.analysis_results?.review_authenticity?.is_fake}
                                    details={product.analysis_results?.review_authenticity?.reason}
                                />
                                <AnalysisResult
                                    title="Seller Behavior"
                                    status={!product.analysis_results?.seller_behavior_analysis?.is_suspicious}
                                    isSuspicious={product.analysis_results?.seller_behavior_analysis?.is_suspicious}
                                    details={
                                        product.analysis_results?.seller_behavior_analysis?.reasons?.length > 0
                                            ? `Reasons: ${product.analysis_results.seller_behavior_analysis.reasons.join(', ')}`
                                            : 'No suspicious activity.'
                                    }
                                />
                            </div>
                        </div>
                        <p className="text-sm text-gray-500 mt-4 text-right">
                            Last Updated: {new Date(product.timestamp).toLocaleString()}
                        </p>
                    </div>
                ))}
            </div>

            <FeedbackForm />
        </div>
    );
}

export default App;
