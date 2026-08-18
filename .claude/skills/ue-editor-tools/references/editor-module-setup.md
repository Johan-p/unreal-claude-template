# Editor Module Setup

Complete boilerplate and registration patterns for Unreal Engine editor modules. All editor extension code must live in a module with `"Type": "Editor"` to ensure it is excluded from packaged builds.

---

## Project Configuration

### .uproject Module Entries

```json
{
  "Modules": [
    {
      "Name": "MyGame",
      "Type": "Runtime",
      "LoadingPhase": "Default"
    },
    {
      "Name": "MyGameEditor",
      "Type": "Editor",
      "LoadingPhase": "PostEngineInit"
    }
  ]
}
```

**LoadingPhase guidance**:

| Phase | Use When |
|---|---|
| `Default` | Module has no editor-UI dependencies |
| `PostEngineInit` | Module registers detail customizations, menus, or editor modes — use this for all editor extension modules |
| `PreDefault` | Module provides services needed before other modules load |

---

## Directory Layout

```
MyProject/
  Source/
    MyGame/                         ← Runtime module
      MyGame.Build.cs
      MyGame.h
      Public/
      Private/
    MyGameEditor/                   ← Editor module
      MyGameEditor.Build.cs
      MyGameEditor.h
      Public/
        Customizations/
          FMyDataAssetCustomization.h
        Modes/
          MyEditorMode.h
        AssetTypes/
          FMyAssetTypeActions.h
      Private/
        MyGameEditorModule.cpp
        Customizations/
          FMyDataAssetCustomization.cpp
        Modes/
          MyEditorMode.cpp
        AssetTypes/
          FMyAssetTypeActions.cpp
```

---

## Build.cs

```csharp
// MyGameEditor.Build.cs
using UnrealBuildTool;

public class MyGameEditor : ModuleRules
{
    public MyGameEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
        });

        PrivateDependencyModuleNames.AddRange(new string[]
        {
            // Editor framework
            "UnrealEd",
            "EditorFramework",

            // Slate for editor UI
            "Slate",
            "SlateCore",           // FAppStyle (Styling/AppStyle.h) lives here

            // Detail panel customization
            "PropertyEditor",      // IDetailCustomization, FPropertyEditorModule

            // Editor subsystems
            "EditorSubsystem",     // UEditorSubsystem base class

            // Blutility (editor utility widgets & scripted actions)
            "Blutility",           // UEditorUtilityWidget, UAssetActionUtility, UActorActionUtility

            // Menus and toolbars
            "ToolMenus",           // UToolMenus

            // Asset definitions and content browser integration
            "AssetDefinition",     // UAssetDefinitionDefault
            "AssetTools",          // IAssetTools (legacy FAssetTypeActions_Base)
            "ContentBrowser",      // Content browser integration (if needed)

            // Editor mode framework
            "EditorInteractiveToolsFramework",  // for UInteractiveTool-based modes (UE5)

            // Input
            "InputCore",           // FKey, EKeys

            // Your runtime module
            "MyGame",
        });

        // Only include these when building for editor targets
        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.AddRange(new string[]
            {
                "EditorScriptingUtilities",  // UEditorAssetLibrary
            });
        }
    }
}
```

---

## Module Header

```cpp
// MyGameEditor.h
#pragma once

#include "Modules/ModuleManager.h"

class FMyGameEditorModule : public IModuleInterface
{
public:
    // IModuleInterface
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;

private:
    void RegisterDetailCustomizations();
    void UnregisterDetailCustomizations();

    // Asset definitions (UAssetDefinitionDefault) and editor modes (UEdMode) are
    // UCLASSes and auto-discovered — no register/unregister functions needed.

    void RegisterMenuExtensions();
};
```

---

## Module Implementation

```cpp
// MyGameEditorModule.cpp
#include "MyGameEditor.h"

// Detail customizations
#include "Customizations/FMyDataAssetCustomization.h"
#include "Customizations/FMyStructCustomization.h"

// Editor modes (UEdMode subclasses)
#include "Modes/MyEditorMode.h"

// Asset definitions (UAssetDefinitionDefault subclasses)
#include "AssetTypes/AssetDefinition_MyAsset.h"

// Runtime types (from MyGame module)
#include "MyDataAsset.h"
#include "MyStruct.h"

// UE headers
#include "PropertyEditorModule.h"
#include "ToolMenus.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/AppStyle.h"

IMPLEMENT_MODULE(FMyGameEditorModule, MyGameEditor)

// ---- StartupModule ----------------------------------------------------------

void FMyGameEditorModule::StartupModule()
{
    RegisterDetailCustomizations();

    // Defer menu registration until Slate is ready
    UToolMenus::RegisterStartupCallback(
        FSimpleMulticastDelegate::FDelegate::CreateRaw(
            this, &FMyGameEditorModule::RegisterMenuExtensions));
}

// ---- ShutdownModule ---------------------------------------------------------

void FMyGameEditorModule::ShutdownModule()
{
    // Menus must be unregistered before PropertyEditor / AssetTools modules unload
    UToolMenus::UnRegisterStartupCallback(this);
    if (UToolMenus* ToolMenus = UToolMenus::TryGet())
    {
        ToolMenus->UnregisterOwner(this);
    }

    UnregisterDetailCustomizations();
}

// ---- Detail Customizations --------------------------------------------------

void FMyGameEditorModule::RegisterDetailCustomizations()
{
    if (!FModuleManager::Get().IsModuleLoaded("PropertyEditor"))
    {
        return;
    }
    FPropertyEditorModule& PropertyModule =
        FModuleManager::LoadModuleChecked<FPropertyEditorModule>("PropertyEditor");

    PropertyModule.RegisterCustomClassLayout(
        UMyDataAsset::StaticClass()->GetFName(),
        FOnGetDetailCustomizationInstance::CreateStatic(
            &FMyDataAssetCustomization::MakeInstance));

    PropertyModule.RegisterCustomPropertyTypeLayout(
        FMyStruct::StaticStruct()->GetFName(),
        FOnGetPropertyTypeCustomizationInstance::CreateStatic(
            &FMyStructCustomization::MakeInstance));

    PropertyModule.NotifyCustomizationModuleChanged();
}

void FMyGameEditorModule::UnregisterDetailCustomizations()
{
    if (!FModuleManager::Get().IsModuleLoaded("PropertyEditor"))
    {
        return;
    }
    FPropertyEditorModule& PropertyModule =
        FModuleManager::GetModuleChecked<FPropertyEditorModule>("PropertyEditor");

    PropertyModule.UnregisterCustomClassLayout(
        UMyDataAsset::StaticClass()->GetFName());
    PropertyModule.UnregisterCustomPropertyTypeLayout(
        FMyStruct::StaticStruct()->GetFName());
}

// ---- Asset Definitions (no module registration needed) ----------------------
//
// UAssetDefinitionDefault subclasses are UCLASSes and are auto-discovered.
// There is nothing to call from StartupModule/ShutdownModule — just declare the
// class in the editor module and it appears in the Content Browser.

// AssetDefinition_MyAsset.h
#include "AssetDefinitionDefault.h"
#include "AssetDefinition_MyAsset.generated.h"

UCLASS()
class UAssetDefinition_MyAsset : public UAssetDefinitionDefault
{
    GENERATED_BODY()
public:
    virtual FText GetAssetDisplayName() const override { return INVTEXT("My Asset"); }
    virtual FLinearColor GetAssetColor() const override { return FLinearColor(FColor(200, 100, 50)); }
    virtual TSoftClassPtr<UObject> GetAssetClass() const override { return UMyAsset::StaticClass(); }

    virtual TConstArrayView<FAssetCategoryPath> GetAssetCategories() const override
    {
        static const FAssetCategoryPath Categories[] = { EAssetCategoryPaths::Misc };
        return Categories;
    }

    // Optional — the base class already routes to UAssetEditorSubsystem.
    virtual EAssetCommandResult OpenAssets(const FAssetOpenArgs& OpenArgs) const override;
};

// Legacy — do not use in new code: FAssetTypeActions_Base with
// IAssetTools::RegisterAssetTypeActions / UnregisterAssetTypeActions (and the
// TArray<TSharedPtr<IAssetTypeActions>> keep-alive) was replaced by the Asset
// Definition system in UE 5.2. See the conversion guide in AssetDefinition.h.

// ---- Editor Modes (no module registration needed) ---------------------------
//
// UEdMode subclasses are UCLASSes and are auto-registered; the mode identity
// comes from the FEditorModeInfo assigned in the UObject constructor.

UCLASS()
class UMyEditorMode : public UEdMode   // Tools/UEdMode.h
{
    GENERATED_BODY()
public:
    const static FEditorModeID EM_MyMode;
    UMyEditorMode();
};

const FEditorModeID UMyEditorMode::EM_MyMode = TEXT("EM_MyEditorMode");

UMyEditorMode::UMyEditorMode()
{
    Info = FEditorModeInfo(
        EM_MyMode,
        FText::FromString("My Editor Mode"),
        FSlateIcon(FAppStyle::GetAppStyleSetName(), "LevelEditor.SelectMode"),
        true  // bVisible in the mode toolbar
    );
}

// Need the legacy Slate toolkit / viewport hooks (Render, HandleClick, MouseMove,
// gizmo widgets)? Derive from UBaseLegacyWidgetEdMode
// (Tools/LegacyEdModeWidgetHelpers.h) instead of UEdMode.
//
// Legacy — do not use in new code: FEdMode with
// FEditorModeRegistry::Get().RegisterMode<T>() / UnregisterMode().

// ---- Menu Extensions --------------------------------------------------------

void FMyGameEditorModule::RegisterMenuExtensions()
{
    FToolMenuOwnerScoped OwnerScoped(this);

    // Main menu extension
    UToolMenu* WindowMenu =
        UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
    {
        FToolMenuSection& Section =
            WindowMenu->FindOrAddSection("MyGameSection");
        Section.Label = FText::FromString("My Game");

        Section.AddMenuEntry(
            "OpenMyPanel",
            FText::FromString("My Tool Panel"),
            FText::FromString("Open the My Game tool panel"),
            FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Settings"),
            FUIAction(FExecuteAction::CreateLambda([]()
            {
                // GEditor->GetEditorSubsystem<UEditorUtilitySubsystem>()
                //     ->SpawnAndRegisterTab(WidgetBP);
            }))
        );
    }
}
```

---

## WITH_EDITOR Guards in Runtime Modules

If a Runtime module needs to reference editor-only functionality (uncommon but valid for things like editor hints):

```cpp
// SomeRuntimeClass.h
UCLASS()
class MYGAME_API UMyRuntimeClass : public UObject
{
    GENERATED_BODY()

public:
#if WITH_EDITOR
    // Editor-only virtual, e.g. for detail panel hints
    virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
    virtual bool CanEditChange(const FProperty* InProperty) const override;
#endif
};

// SomeRuntimeClass.cpp
#if WITH_EDITOR
void UMyRuntimeClass::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    Super::PostEditChangeProperty(PropertyChangedEvent);
    const FName PropertyName = PropertyChangedEvent.GetPropertyName();
    if (PropertyName == GET_MEMBER_NAME_CHECKED(UMyRuntimeClass, Speed))
    {
        Speed = FMath::Clamp(Speed, 0.f, MaxSpeed);
    }
}

bool UMyRuntimeClass::CanEditChange(const FProperty* InProperty) const
{
    if (!Super::CanEditChange(InProperty))
    {
        return false;
    }
    if (InProperty->GetFName() == GET_MEMBER_NAME_CHECKED(UMyRuntimeClass, AdvancedSetting))
    {
        return bEnableAdvanced;
    }
    return true;
}
#endif
```

---

## Asset Factory (UFactory) Boilerplate

Required to support "right-click > Create" in the Content Browser for a custom asset type:

```cpp
// MyCustomAssetFactory.h
#pragma once
#include "Factories/Factory.h"
#include "MyCustomAssetFactory.generated.h"

UCLASS()
class UMyCustomAssetFactory : public UFactory
{
    GENERATED_BODY()

public:
    UMyCustomAssetFactory();

    virtual UObject* FactoryCreateNew(
        UClass* Class,
        UObject* InParent,
        FName Name,
        EObjectFlags Flags,
        UObject* Context,
        FFeedbackContext* Warn) override;

    virtual bool ShouldShowInNewMenu() const override { return true; }
};

// MyCustomAssetFactory.cpp
#include "MyCustomAssetFactory.h"
#include "MyCustomAsset.h"

UMyCustomAssetFactory::UMyCustomAssetFactory()
{
    SupportedClass = UMyCustomAsset::StaticClass();
    bCreateNew = true;
    bEditAfterNew = true;  // open editor immediately after creation
}

UObject* UMyCustomAssetFactory::FactoryCreateNew(
    UClass* Class,
    UObject* InParent,
    FName Name,
    EObjectFlags Flags,
    UObject* Context,
    FFeedbackContext* Warn)
{
    return NewObject<UMyCustomAsset>(InParent, Class, Name, Flags);
}
```

The factory is auto-discovered by the editor; no explicit registration is needed. The `UFactory` subclass must be in the editor module.

---

## Module Dependency Graph

```
MyGameEditor (Type: Editor)
    depends on → MyGame (Type: Runtime)
    depends on → PropertyEditor, UnrealEd, Blutility, ToolMenus, AssetTools
    depends on → Slate, SlateCore

MyGame (Type: Runtime)
    no editor dependencies
    uses WITH_EDITOR guards for PostEditChangeProperty etc.
```

---

## Checklist: New Editor Module

- [ ] `"Type": "Editor"` in .uproject
- [ ] `"LoadingPhase": "PostEngineInit"` in .uproject
- [ ] `Build.cs` references `UnrealEd`, `PropertyEditor`, `ToolMenus`, `Blutility` as needed
- [ ] `IMPLEMENT_MODULE(FMyEditorModule, MyEditorModuleName)` in .cpp
- [ ] All registrations in `StartupModule`
- [ ] All unregistrations in `ShutdownModule` (guarded with `IsModuleLoaded` checks)
- [ ] Menu registrations wrapped in `UToolMenus::RegisterStartupCallback`
- [ ] Menu unregistration: `UnRegisterStartupCallback` + `UnregisterOwner`
- [ ] `NotifyCustomizationModuleChanged()` called after detail customization registration
- [ ] No `#include "EdMode.h"` or other editor headers pulled into Runtime module headers
