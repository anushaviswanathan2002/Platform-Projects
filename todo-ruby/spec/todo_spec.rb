require "spec_helper"

RSpec.describe Todo::List do
  subject(:list) { described_class.new }

  describe "#add" do
    it "adds a new pending item with a unique incrementing id" do
      a = list.add("buy milk")
      b = list.add("buy bread")
      expect(list.items.size).to eq(2)
      expect(a).to eq(1)
      expect(b).to eq(2)
      expect(list.items.first).to be_done?.and have_attributes(title: "buy milk")
    end

    it "rejects empty/whitespace titles" do
      expect { list.add("") }.to raise_error(ArgumentError)
      expect { list.add("   ") }.to raise_error(ArgumentError)
      expect { list.add(nil) }.to raise_error(ArgumentError)
    end
  end

  describe "#complete" do
    it "marks the item with the given id as done" do
      id = list.add("pay rent")
      list.complete(id)
      expect(list.items.find { |i| i.id == id }).to be_done
    end

    it "raises if no item with that id" do
      expect { list.complete(42) }.to raise_error(ArgumentError)
    end
  end

  describe "#pending" do
    it "returns only items that are not done" do
      a = list.add("task a")
      _b = list.add("task b")
      list.complete(a)
      pending = list.pending
      expect(pending.size).to eq(1)
      expect(pending.first.title).to eq("task b")
    end
  end

  describe "#remove" do
    it "removes the item with the given id" do
      id = list.add("temporary")
      list.remove(id)
      expect(list.items).to be_empty
    end
  end
end
