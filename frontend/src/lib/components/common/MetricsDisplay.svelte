<!--
  MetricsDisplay Component

  Displays georectification quality metrics including RMSE, GCP statistics,
  and residual statistics in a clean, organized layout.

  Usage:
    <MetricsDisplay metrics={processMetrics} />
-->
<script lang="ts">
	import type { ProcessMetrics } from '$lib/types';

	/** Process metrics to display */
	export let metrics: ProcessMetrics;

	// Format number with specified decimal places
	function formatNumber(value: number | undefined, decimals: number = 2): string {
		if (value === undefined || value === null) return '-';
		return value.toFixed(decimals);
	}

	// Get quality level based on RMSE
	function getQualityLevel(rmse: number): { label: string; color: string; bgColor: string } {
		if (rmse < 1) {
			return { label: 'Excellent', color: 'text-green-700', bgColor: 'bg-green-100' };
		} else if (rmse < 3) {
			return { label: 'Good', color: 'text-blue-700', bgColor: 'bg-blue-100' };
		} else if (rmse < 5) {
			return { label: 'Acceptable', color: 'text-yellow-700', bgColor: 'bg-yellow-100' };
		} else {
			return { label: 'Poor', color: 'text-red-700', bgColor: 'bg-red-100' };
		}
	}

	$: quality = getQualityLevel(metrics.rmse);
</script>

<div class="space-y-6">
	<!-- Main RMSE Metric -->
	<div class="text-center p-6 bg-gray-50 rounded-lg">
		<div class="text-sm font-medium text-gray-500 uppercase tracking-wide">
			Root Mean Square Error (RMSE)
		</div>
		<div class="mt-2 flex items-center justify-center gap-3">
			<span class="text-4xl font-bold text-gray-900">
				{formatNumber(metrics.rmse)}
			</span>
			<span class="text-xl text-gray-500">pixels</span>
		</div>
		<div class="mt-2">
			<span class={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${quality.bgColor} ${quality.color}`}>
				{quality.label}
			</span>
		</div>
	</div>

	<!-- GCP Statistics -->
	<div class="grid grid-cols-2 gap-4">
		<div class="p-4 bg-white border border-gray-200 rounded-lg">
			<div class="text-sm font-medium text-gray-500">Active GCPs</div>
			<div class="mt-1 text-2xl font-semibold text-gray-900">
				{metrics.gcp_count}
				<span class="text-lg text-gray-500">/ {metrics.gcp_total}</span>
			</div>
			<div class="mt-1 text-xs text-gray-400">
				{((metrics.gcp_count / metrics.gcp_total) * 100).toFixed(0)}% used
			</div>
		</div>

		<div class="p-4 bg-white border border-gray-200 rounded-lg">
			<div class="text-sm font-medium text-gray-500">GCP Usage Rate</div>
			<div class="mt-2">
				<div class="w-full bg-gray-200 rounded-full h-2">
					<div
						class="bg-primary-600 h-2 rounded-full"
						style="width: {(metrics.gcp_count / metrics.gcp_total) * 100}%"
					></div>
				</div>
			</div>
		</div>
	</div>

	<!-- Residual Statistics -->
	{#if metrics.residual_mean !== undefined}
		<div>
			<h4 class="text-sm font-medium text-gray-700 mb-3">Residual Statistics</h4>
			<div class="grid grid-cols-3 gap-4">
				<div class="p-4 bg-white border border-gray-200 rounded-lg text-center">
					<div class="text-sm font-medium text-gray-500">Mean</div>
					<div class="mt-1 text-xl font-semibold text-gray-900">
						{formatNumber(metrics.residual_mean)}
					</div>
					<div class="text-xs text-gray-400">pixels</div>
				</div>

				<div class="p-4 bg-white border border-gray-200 rounded-lg text-center">
					<div class="text-sm font-medium text-gray-500">Std Dev</div>
					<div class="mt-1 text-xl font-semibold text-gray-900">
						{formatNumber(metrics.residual_std)}
					</div>
					<div class="text-xs text-gray-400">pixels</div>
				</div>

				<div class="p-4 bg-white border border-gray-200 rounded-lg text-center">
					<div class="text-sm font-medium text-gray-500">Max</div>
					<div class="mt-1 text-xl font-semibold text-gray-900">
						{formatNumber(metrics.residual_max)}
					</div>
					<div class="text-xs text-gray-400">pixels</div>
				</div>
			</div>
		</div>
	{/if}
</div>
