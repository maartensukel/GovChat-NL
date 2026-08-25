<script lang="ts">
	import { models, settings, user } from '$lib/stores';
	// Govchat
	import { filteredModels } from '$lib/stores/appModels';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Selector from './ModelSelector/Selector.svelte';

	import { updateUserSettings } from '$lib/apis/users';
	import equal from 'fast-deep-equal';
	const i18n = getContext('i18n');

	export let selectedModels = [''];
	export let disabled = false;

	export let showSetDefault = true;
	export let triggerClassName = 'text-lg';
	export let className = undefined;
	export let placement: 'top' | 'bottom' | 'auto' = 'bottom';
	export let align: 'start' | 'end' = 'start';
	// Govchat
	export let useAppFilter = false; // New prop to enable app-specific filtering

	// Use either filtered models or all models based on useAppFilter prop.
	// NB: alleen de lijst met keuzes wordt gefilterd; deze component schrijft zelf
	// nooit naar de gebonden selectedModels — dat veroorzaakt in Svelte 5 een
	// update-lus (effect_update_depth_exceeded) met de parent-binding.
	$: availableModels = useAppFilter ? $filteredModels : $models;

	let compareModels = selectedModels.length > 1;

	const saveDefaultModel = async () => {
		const hasEmptyModel = selectedModels.filter((it) => it === '');
		if (hasEmptyModel.length) {
			toast.error($i18n.t('Choose a model before saving...'));
			return;
		}
		settings.set({ ...$settings, models: selectedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });

		toast.success($i18n.t('Default model updated'));
	};

	const pinModelHandler = async (modelId) => {
		let pinnedModels = $settings?.pinnedModels ?? [];

		if (pinnedModels.includes(modelId)) {
			pinnedModels = pinnedModels.filter((id) => id !== modelId);
		} else {
			pinnedModels = [...new Set([...pinnedModels, modelId])];
		}

		settings.set({ ...$settings, pinnedModels: pinnedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	$: if (selectedModels.length > 0 && $models.length > 0) {
		const _selectedModels = selectedModels.map((model) =>
			$models.map((m) => m.id).includes(model) ? model : ''
		);

		if (!equal(_selectedModels, selectedModels)) {
			selectedModels = _selectedModels;
		}
	}

	$: if (selectedModels.length > 1 && !compareModels) {
		compareModels = true;
	}
</script>

<div class="flex min-w-0 max-w-full flex-col items-start">
	<div class="flex min-w-0 max-w-full">
		<div class="min-w-0 max-w-full overflow-hidden">
			<div class="min-w-0 max-w-full">
				<Selector
					id="model"
					placeholder={$i18n.t('Select a model')}
					items={availableModels.map((model) => ({
						value: model.id,
						label: model.name,
						model: model
					}))}
					{pinModelHandler}
					{className}
					{triggerClassName}
					{placement}
					{align}
					{showSetDefault}
					onSetDefault={saveDefaultModel}
					multipleEnabled={$user?.role === 'admin' ||
						($user?.permissions?.chat?.multiple_models ?? true)}
					{disabled}
					bind:compareEnabled={compareModels}
					bind:values={selectedModels}
				/>
			</div>
		</div>
	</div>
</div>
